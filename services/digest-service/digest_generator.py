"""
Генератор дайджестов
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import grpc
import json

from database import db_manager
from config import config

# Импорт gRPC клиентов
import sys
sys.path.append('/app')
from shared.proto import ranking_service_pb2, ranking_service_pb2_grpc
from shared.proto import user_service_pb2, user_service_pb2_grpc

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Генератор персонализированных дайджестов"""
    
    def __init__(self):
        self.ranking_channel = None
        self.ranking_stub = None
        self.user_channel = None
        self.user_stub = None
        self._connect_to_ranking_service()
        self._connect_to_user_service()
    
    def _connect_to_ranking_service(self):
        """Подключение к Ranking Service"""
        try:
            ranking_address = f"{config.RANKING_SERVICE_HOST}:{config.RANKING_SERVICE_PORT}"
            self.ranking_channel = grpc.insecure_channel(ranking_address)
            self.ranking_stub = ranking_service_pb2_grpc.RankingServiceStub(self.ranking_channel)
            logger.info(f"Connected to Ranking Service at {ranking_address}")
        except Exception as e:
            logger.error(f"Failed to connect to Ranking Service: {e}")
    
    def _connect_to_user_service(self):
        """Подключение к User Service"""
        try:
            user_address = f"{config.USER_SERVICE_HOST}:{config.USER_SERVICE_PORT}"
            self.user_channel = grpc.insecure_channel(user_address)
            self.user_stub = user_service_pb2_grpc.UserServiceStub(self.user_channel)
            logger.info(f"Connected to User Service at {user_address}")
        except Exception as e:
            logger.error(f"Failed to connect to User Service: {e}")
    
    def _get_user_detail_level(self, user_id: int) -> str:
        """
        Получить уровень детализации из настроек пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Уровень детализации (very_interested, interested, maybe, not_interested)
        """
        try:
            if not self.user_stub:
                logger.warning("User Service not available, using default detail level")
                return "interested"
            
            request = user_service_pb2.GetUserProfileRequest(user_id=user_id)
            response = self.user_stub.GetUserProfile(request, timeout=5)
            
            if response.success and response.preferences_json:
                preferences = json.loads(response.preferences_json)
                detail_level = preferences.get("detail_level", "interested")
                logger.info(f"User {user_id} detail level: {detail_level}")
                return detail_level
            else:
                logger.warning(f"No preferences found for user {user_id}, using default")
                return "interested"
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting user preferences: {e.code()} - {e.details()}")
            return "interested"
        except Exception as e:
            logger.error(f"Error getting user detail level: {e}")
            return "interested"
    
    def generate_digest(
        self,
        user_id: int,
        max_items: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Генерация дайджеста для пользователя
        
        Args:
            user_id: ID пользователя
            max_items: Максимальное количество элементов (по умолчанию из конфига)
            
        Returns:
            Словарь с данными дайджеста или None при ошибке
        """
        if max_items is None:
            max_items = config.DEFAULT_MAX_ITEMS
        
        try:
            session = db_manager.get_session()
            
            # 1. Получить подписки пользователя
            source_ids = db_manager.get_user_subscriptions(session, user_id)
            if not source_ids:
                logger.warning(f"User {user_id} has no subscriptions")
                session.close()
                return None
            
            # 2. Определить период для контента
            period_end = datetime.utcnow()
            
            # Получаем последний дайджест для определения начала периода
            from database import Digest
            last_digest = session.query(Digest).filter(
                Digest.user_id == user_id
            ).order_by(Digest.created_at.desc()).first()
            
            if last_digest:
                period_start = last_digest.period_end
            else:
                # Если это первый дайджест, берем контент за последние 24 часа
                period_start = period_end - timedelta(hours=24)
            
            # 3. Получить новый контент
            content_list = db_manager.get_new_content(
                session,
                source_ids,
                period_start,
                limit=100
            )
            
            if not content_list:
                logger.info(f"No new content for user {user_id}")
                session.close()
                return {
                    'user_id': user_id,
                    'period_start': period_start,
                    'period_end': period_end,
                    'items': [],
                    'message': 'Нет нового контента за этот период'
                }
            
            # 4. Ранжировать контент через Ranking Service
            content_ids = [content.content_id for content in content_list]
            ranked_ids = self._rank_content(user_id, content_ids, max_items)
            
            if not ranked_ids:
                logger.warning(f"Ranking failed for user {user_id}, using chronological order")
                ranked_ids = content_ids[:max_items]
            
            # 5. Получить уровень детализации пользователя
            detail_level = self._get_user_detail_level(user_id)
            
            # 6. Получить детальную информацию о контенте
            content_details = db_manager.get_content_with_source(session, ranked_ids)
            
            # 7. Формировать элементы дайджеста с адаптивной длиной
            digest_items = []
            for content in content_details:
                # Используем summary как аннотацию, адаптируя длину
                annotation = self._format_annotation(
                    content.get('summary', content.get('text', '')),
                    detail_level
                )
                
                digest_items.append({
                    'content_id': content['content_id'],
                    'annotation': annotation,
                    'source_name': content['source_name'],
                    'original_url': content['original_url'],
                    'published_at': content['published_at'],
                    'platform': content['platform'],
                    'topic_tags': content.get('topic_tags', []),
                    'detail_level': detail_level
                })
            
            # 8. Сохранить дайджест в БД
            digest_id = db_manager.save_digest(
                session,
                user_id,
                period_start,
                period_end,
                digest_items
            )
            
            session.close()
            
            if digest_id:
                logger.info(f"Digest generated successfully: digest_id={digest_id}, user_id={user_id}, items={len(digest_items)}")
                return {
                    'digest_id': digest_id,
                    'user_id': user_id,
                    'period_start': period_start,
                    'period_end': period_end,
                    'items': digest_items
                }
            else:
                logger.error(f"Failed to save digest for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating digest for user {user_id}: {e}", exc_info=True)
            return None
    
    def _rank_content(
        self,
        user_id: int,
        content_ids: List[int],
        limit: int
    ) -> List[int]:
        """
        Ранжировать контент через Ranking Service
        
        Args:
            user_id: ID пользователя
            content_ids: Список ID контента
            limit: Максимальное количество элементов
            
        Returns:
            Список отранжированных ID контента
        """
        try:
            if not self.ranking_stub:
                logger.warning("Ranking Service not available, skipping ranking")
                return content_ids[:limit]
            
            request = ranking_service_pb2.RankContentRequest(
                user_id=user_id,
                content_ids=content_ids,
                limit=limit
            )
            
            response = self.ranking_stub.RankContent(request, timeout=10)
            
            if response.ranked_content:
                return [item.content_id for item in response.ranked_content]
            else:
                return content_ids[:limit]
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error ranking content: {e.code()} - {e.details()}")
            return content_ids[:limit]
        except Exception as e:
            logger.error(f"Error ranking content: {e}")
            return content_ids[:limit]
    
    def _format_annotation(self, text: str, detail_level: str) -> str:
        """
        Форматировать аннотацию в соответствии с уровнем детализации
        
        Args:
            text: Исходный текст (summary или полный текст)
            detail_level: Уровень детализации
            
        Returns:
            Отформатированная аннотация
        """
        # Маппинг уровней детализации на максимальную длину в символах
        length_map = {
            "very_interested": 800,   # ~200-300 слов
            "interested": 500,        # ~100-150 слов
            "maybe": 300,             # ~50-100 слов
            "not_interested": 150     # ~30 слов (только заголовок)
        }
        
        max_length = length_map.get(detail_level, 500)
        
        if len(text) <= max_length:
            return text
        
        # Обрезаем до максимальной длины, стараясь не разрывать предложения
        truncated = text[:max_length]
        
        # Ищем последнюю точку, восклицательный или вопросительный знак
        last_sentence_end = max(
            truncated.rfind('.'),
            truncated.rfind('!'),
            truncated.rfind('?')
        )
        
        if last_sentence_end > max_length * 0.7:  # Если нашли точку в последних 30%
            return truncated[:last_sentence_end + 1]
        else:
            return truncated.rstrip() + "..."
    
    def format_digest_text(self, digest_data: Dict[str, Any]) -> str:
        """
        Форматировать дайджест для отправки пользователю
        
        Args:
            digest_data: Данные дайджеста
            
        Returns:
            Отформатированный текст дайджеста
        """
        items = digest_data.get('items', [])
        
        if not items:
            return digest_data.get('message', 'Нет нового контента за этот период 📭')
        
        # Заголовок
        period_start = digest_data.get('period_start')
        period_end = digest_data.get('period_end')
        
        if isinstance(period_start, datetime):
            period_start = period_start.strftime('%d.%m.%Y %H:%M')
        if isinstance(period_end, datetime):
            period_end = period_end.strftime('%d.%m.%Y %H:%M')
        
        text = f"📰 <b>Ваш персональный дайджест</b>\n"
        text += f"📅 Период: {period_start} - {period_end}\n"
        text += f"📊 Найдено материалов: {len(items)}\n\n"
        text += "─" * 40 + "\n\n"
        
        # Элементы дайджеста
        for idx, item in enumerate(items, 1):
            text += f"<b>{idx}. {self._get_platform_emoji(item.get('platform', ''))} "
            
            # Добавляем теги если есть
            tags = item.get('topic_tags', [])
            if tags:
                text += f"{', '.join(tags[:3])}</b>\n"
            else:
                text += "Новость</b>\n"
            
            # Аннотация (уже отформатирована с учетом detail_level)
            annotation = item.get('annotation', '')
            text += f"{annotation}\n\n"
            
            # Источник и ссылка
            source_name = item.get('source_name', 'Unknown')
            original_url = item.get('original_url', '')
            
            if original_url:
                text += f"🔗 <a href='{original_url}'>Читать полностью</a> | "
            text += f"📡 {source_name}\n"
            
            # Кнопки обратной связи (будут добавлены в Bot Service)
            text += f"<code>/feedback_{item['content_id']}</code>\n\n"
            
            if idx < len(items):
                text += "─" * 40 + "\n\n"
        
        # Футер
        text += "\n💡 <i>Оцените качество дайджеста: /rate</i>"
        
        return text
    
    def _get_platform_emoji(self, platform: str) -> str:
        """Получить эмодзи для платформы"""
        emoji_map = {
            'telegram': '✈️',
            'vk': '🔵',
            'youtube': '▶️',
        }
        return emoji_map.get(platform.lower(), '📄')
    
    def close(self):
        """Закрыть соединения"""
        if self.ranking_channel:
            self.ranking_channel.close()
        if self.user_channel:
            self.user_channel.close()


# Глобальный экземпляр генератора
digest_generator = DigestGenerator()
