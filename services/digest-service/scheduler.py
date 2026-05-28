"""
Планировщик генерации дайджестов
"""

import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import db_manager
from digest_generator import digest_generator
from config import config

logger = logging.getLogger(__name__)


class DigestScheduler:
    """Планировщик автоматической генерации дайджестов"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        logger.info("Digest Scheduler initialized")
    
    def start(self):
        """Запуск планировщика"""
        if not config.SCHEDULER_ENABLED:
            logger.info("Scheduler is disabled in config")
            return
        
        # Добавляем задачу проверки расписаний
        self.scheduler.add_job(
            self.check_and_generate_digests,
            trigger=IntervalTrigger(seconds=config.SCHEDULER_CHECK_INTERVAL),
            id='digest_check',
            name='Check and generate digests',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"Scheduler started with check interval: {config.SCHEDULER_CHECK_INTERVAL}s")
    
    def stop(self):
        """Остановка планировщика"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
    
    async def check_and_generate_digests(self):
        """
        Проверка расписаний и генерация дайджестов
        Вызывается периодически планировщиком
        """
        try:
            logger.debug("Checking for users who need digests...")
            
            session = db_manager.get_session()
            users_to_process = db_manager.get_users_for_digest(session)
            session.close()
            
            if not users_to_process:
                logger.debug("No users need digests at this time")
                return
            
            logger.info(f"Found {len(users_to_process)} users who need digests")
            
            # Генерируем дайджесты для каждого пользователя
            for user_info in users_to_process:
                try:
                    await self.generate_and_send_digest(user_info)
                except Exception as e:
                    logger.error(f"Error processing user {user_info['user_id']}: {e}", exc_info=True)
            
            logger.info(f"Digest generation cycle completed for {len(users_to_process)} users")
            
        except Exception as e:
            logger.error(f"Error in check_and_generate_digests: {e}", exc_info=True)
    
    async def generate_and_send_digest(self, user_info: dict):
        """
        Генерация и отправка дайджеста пользователю
        
        Args:
            user_info: Информация о пользователе
        """
        user_id = user_info['user_id']
        telegram_id = user_info.get('telegram_id')
        
        try:
            logger.info(f"Generating digest for user {user_id}")
            
            # 1. Генерируем дайджест
            digest_data = digest_generator.generate_digest(user_id)
            
            if not digest_data:
                logger.warning(f"Failed to generate digest for user {user_id}")
                return
            
            # 2. Форматируем текст дайджеста
            digest_text = digest_generator.format_digest_text(digest_data)
            
            # 3. Отправляем через Bot Service (если доступен)
            if telegram_id:
                await self._send_to_bot_service(telegram_id, digest_text, digest_data)
            else:
                logger.warning(f"User {user_id} has no telegram_id, cannot send digest")
            
            logger.info(f"Digest successfully generated and sent for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error generating/sending digest for user {user_id}: {e}", exc_info=True)
    
    async def _send_to_bot_service(
        self,
        telegram_id: str,
        digest_text: str,
        digest_data: dict
    ):
        """
        Отправка дайджеста через Bot Service
        
        Args:
            telegram_id: Telegram ID пользователя
            digest_text: Отформатированный текст дайджеста
            digest_data: Данные дайджеста
        """
        try:
            # TODO: Реализовать отправку через gRPC или HTTP API Bot Service
            # Пока просто логируем
            logger.info(f"Would send digest to telegram_id={telegram_id}")
            logger.debug(f"Digest text length: {len(digest_text)} characters")
            
            # В будущем здесь будет вызов Bot Service API
            # Например:
            # bot_client.send_digest(telegram_id, digest_text, digest_data)
            
        except Exception as e:
            logger.error(f"Error sending digest to Bot Service: {e}")
    
    def trigger_manual_generation(self, user_id: int) -> dict:
        """
        Ручная генерация дайджеста для пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Данные сгенерированного дайджеста
        """
        try:
            logger.info(f"Manual digest generation triggered for user {user_id}")
            digest_data = digest_generator.generate_digest(user_id)
            
            if digest_data:
                logger.info(f"Manual digest generated successfully for user {user_id}")
            else:
                logger.warning(f"Failed to generate manual digest for user {user_id}")
            
            return digest_data
            
        except Exception as e:
            logger.error(f"Error in manual digest generation: {e}", exc_info=True)
            return None


# Глобальный экземпляр планировщика
digest_scheduler = DigestScheduler()
