"""
Telegram Collector - основной модуль сбора контента из Telegram-каналов
"""

import asyncio
import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import Channel, User
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    ChannelPrivateError,
    UsernameInvalidError
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from config import settings
from rabbitmq_publisher import RabbitMQPublisher


logger = structlog.get_logger(__name__)


class TelegramCollector:
    """Коллектор контента из Telegram-каналов"""
    
    def __init__(self):
        self.client = None
        self.publisher = RabbitMQPublisher()
        self.engine = None
        self.async_session = None
        self.monitored_channels = set()
        self.last_message_ids = {}  # Хранение ID последних обработанных сообщений
        
    async def initialize(self):
        """Инициализация клиента и подключений"""
        try:
            # Инициализация Telegram клиента
            self.client = TelegramClient(
                settings.telegram_session_name,
                settings.telegram_api_id,
                settings.telegram_api_hash
            )
            
            await self.client.start()
            
            # Проверка авторизации
            if not await self.client.is_user_authorized():
                logger.warning("telegram_not_authorized")
                if settings.telegram_phone:
                    await self.client.send_code_request(settings.telegram_phone)
                    logger.info("code_sent_to_phone", phone=settings.telegram_phone)
                else:
                    logger.error("telegram_phone_not_configured")
                    raise ValueError("Telegram phone number not configured")
            
            logger.info("telegram_client_initialized")
            
            # Инициализация подключения к БД
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_pre_ping=True
            )
            
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("database_connection_initialized")
            
            # Подключение к RabbitMQ
            self.publisher.connect()
            
        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            raise
    
    async def get_telegram_sources(self) -> List[Dict[str, Any]]:
        """
        Получение списка Telegram-источников из базы данных
        
        Returns:
            List[Dict]: Список источников с их параметрами
        """
        try:
            async with self.async_session() as session:
                query = text("""
                    SELECT source_id, url, topic
                    FROM content_sources
                    WHERE platform_type = 'telegram'
                    AND url IS NOT NULL
                """)
                
                result = await session.execute(query)
                sources = []
                
                for row in result:
                    sources.append({
                        'source_id': row[0],
                        'url': row[1],
                        'topic': row[2]
                    })
                
                logger.info("sources_fetched", count=len(sources))
                return sources
                
        except Exception as e:
            logger.error("sources_fetch_failed", error=str(e))
            return []
    
    async def extract_channel_username(self, url: str) -> Optional[str]:
        """
        Извлечение username канала из URL
        
        Args:
            url: URL канала (https://t.me/channel_name или @channel_name)
            
        Returns:
            str: Username канала или None
        """
        if url.startswith('@'):
            return url[1:]
        elif 't.me/' in url:
            parts = url.split('t.me/')
            if len(parts) > 1:
                username = parts[1].strip('/').split('/')[0]
                return username
        return None
    
    async def get_channel_entity(self, username: str):
        """
        Получение entity канала по username
        
        Args:
            username: Username канала
            
        Returns:
            Channel entity или None
        """
        try:
            entity = await self.client.get_entity(username)
            if isinstance(entity, Channel):
                return entity
            else:
                logger.warning("not_a_channel", username=username, type=type(entity).__name__)
                return None
        except UsernameInvalidError:
            logger.error("invalid_username", username=username)
            return None
        except ChannelPrivateError:
            logger.error("channel_private", username=username)
            return None
        except Exception as e:
            logger.error("get_entity_failed", username=username, error=str(e))
            return None
    
    async def collect_channel_messages(
        self,
        source_id: int,
        channel_username: str,
        limit: int = None
    ) -> int:
        """
        Сбор сообщений из канала
        
        Args:
            source_id: ID источника в БД
            channel_username: Username канала
            limit: Максимальное количество сообщений
            
        Returns:
            int: Количество собранных сообщений
        """
        try:
            entity = await self.get_channel_entity(channel_username)
            if not entity:
                return 0
            
            # Получение последнего обработанного message_id
            last_message_id = self.last_message_ids.get(source_id, 0)
            
            collected_count = 0
            limit = limit or settings.max_messages_per_channel
            
            # Получение сообщений
            async for message in self.client.iter_messages(
                entity,
                limit=limit,
                reverse=False
            ):
                # Пропуск уже обработанных сообщений
                if message.id <= last_message_id:
                    continue
                
                # Пропуск сообщений без текста
                if not message.text:
                    continue
                
                # Формирование данных сообщения
                message_data = await self.format_message(
                    source_id=source_id,
                    channel_username=channel_username,
                    message=message
                )
                
                # Публикация в RabbitMQ
                if self.publisher.publish_message(message_data):
                    collected_count += 1
                    
                    # Обновление последнего обработанного ID
                    if message.id > last_message_id:
                        self.last_message_ids[source_id] = message.id
                
                # Небольшая задержка для избежания rate limiting
                await asyncio.sleep(0.1)
            
            logger.info(
                "channel_collected",
                channel=channel_username,
                count=collected_count,
                last_message_id=self.last_message_ids.get(source_id, 0)
            )
            
            return collected_count
            
        except FloodWaitError as e:
            logger.warning(
                "flood_wait_error",
                channel=channel_username,
                wait_seconds=e.seconds
            )
            await asyncio.sleep(e.seconds)
            return 0
            
        except Exception as e:
            logger.error(
                "channel_collection_failed",
                channel=channel_username,
                error=str(e)
            )
            return 0
    
    async def format_message(
        self,
        source_id: int,
        channel_username: str,
        message
    ) -> Dict[str, Any]:
        """
        Форматирование сообщения для отправки в RabbitMQ
        
        Args:
            source_id: ID источника в БД
            channel_username: Username канала
            message: Объект сообщения Telethon
            
        Returns:
            Dict: Отформатированные данные сообщения
        """
        # Извлечение медиа URL (если есть)
        media_urls = []
        if message.media:
            # Для простоты пока оставляем пустым, можно расширить позже
            pass
        
        # Формирование URL оригинального сообщения
        original_url = f"https://t.me/{channel_username}/{message.id}"
        
        # Получение информации об авторе
        author = channel_username
        if message.forward:
            if message.forward.from_name:
                author = message.forward.from_name
            elif message.forward.from_id:
                try:
                    forward_entity = await self.client.get_entity(message.forward.from_id)
                    if isinstance(forward_entity, User):
                        author = forward_entity.first_name or forward_entity.username
                    elif isinstance(forward_entity, Channel):
                        author = forward_entity.title or forward_entity.username
                except:
                    pass
        
        # Формирование сообщения по схеме RawContentMessage
        message_data = {
            "message_type": "raw_content",
            "platform": "telegram",
            "source_id": source_id,
            "source_url": f"https://t.me/{channel_username}",
            "content": {
                "text": message.text,
                "author": author,
                "published_at": message.date.isoformat(),
                "media_urls": media_urls,
                "original_url": original_url
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return message_data
    
    async def start_monitoring(self):
        """
        Запуск мониторинга каналов в режиме реального времени
        """
        logger.info("starting_realtime_monitoring")
        
        @self.client.on(events.NewMessage())
        async def handler(event):
            try:
                # Проверка, что сообщение из отслеживаемого канала
                if event.chat_id not in self.monitored_channels:
                    return
                
                # Получение информации о канале
                chat = await event.get_chat()
                if not isinstance(chat, Channel):
                    return
                
                channel_username = chat.username
                if not channel_username:
                    return
                
                # Поиск source_id
                source_id = None
                async with self.async_session() as session:
                    query = text("""
                        SELECT source_id FROM content_sources
                        WHERE platform_type = 'telegram'
                        AND url LIKE :pattern
                        LIMIT 1
                    """)
                    result = await session.execute(
                        query,
                        {"pattern": f"%{channel_username}%"}
                    )
                    row = result.first()
                    if row:
                        source_id = row[0]
                
                if not source_id:
                    return
                
                # Формирование и публикация сообщения
                message_data = await self.format_message(
                    source_id=source_id,
                    channel_username=channel_username,
                    message=event.message
                )
                
                self.publisher.publish_message(message_data)
                
                logger.info(
                    "realtime_message_collected",
                    channel=channel_username,
                    message_id=event.message.id
                )
                
            except Exception as e:
                logger.error("realtime_handler_error", error=str(e))
        
        # Получение списка каналов для мониторинга
        sources = await self.get_telegram_sources()
        
        for source in sources:
            username = await self.extract_channel_username(source['url'])
            if username:
                entity = await self.get_channel_entity(username)
                if entity:
                    self.monitored_channels.add(entity.id)
                    logger.info("channel_added_to_monitoring", channel=username)
        
        logger.info(
            "monitoring_started",
            channels_count=len(self.monitored_channels)
        )
        
        # Запуск клиента (блокирующий вызов)
        await self.client.run_until_disconnected()
    
    async def run_polling_mode(self):
        """
        Запуск в режиме периодического опроса каналов
        """
        logger.info("starting_polling_mode", interval=settings.poll_interval)
        
        while True:
            try:
                # Получение списка источников
                sources = await self.get_telegram_sources()
                
                total_collected = 0
                
                for source in sources:
                    username = await self.extract_channel_username(source['url'])
                    if username:
                        count = await self.collect_channel_messages(
                            source_id=source['source_id'],
                            channel_username=username
                        )
                        total_collected += count
                        
                        # Задержка между каналами
                        await asyncio.sleep(2)
                
                logger.info(
                    "polling_cycle_completed",
                    total_collected=total_collected,
                    sources_count=len(sources)
                )
                
                # Ожидание перед следующим циклом
                await asyncio.sleep(settings.poll_interval)
                
            except Exception as e:
                logger.error("polling_cycle_error", error=str(e))
                await asyncio.sleep(30)  # Ожидание перед повторной попыткой
    
    async def shutdown(self):
        """Корректное завершение работы коллектора"""
        logger.info("shutting_down_collector")
        
        try:
            if self.client:
                await self.client.disconnect()
                logger.info("telegram_client_disconnected")
            
            if self.publisher:
                self.publisher.close()
            
            if self.engine:
                await self.engine.dispose()
                logger.info("database_connection_closed")
                
        except Exception as e:
            logger.error("shutdown_error", error=str(e))
