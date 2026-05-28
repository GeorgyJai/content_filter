"""
Главный модуль Summarization Service
Обработка сырого контента: суммаризация, анализ тональности, генерация эмбеддингов
"""

import signal
import sys
import structlog
from typing import Dict, Any, Optional
from datetime import datetime

from config import settings
from nlp_processor import NLPProcessor
from rabbitmq_consumer import RabbitMQConsumer
from rabbitmq_publisher import RabbitMQPublisher
from database import DatabaseManager

# Настройка структурированного логирования
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()


class SummarizationService:
    """Основной класс сервиса суммаризации"""
    
    def __init__(self):
        """Инициализация сервиса"""
        self.nlp_processor: Optional[NLPProcessor] = None
        self.consumer: Optional[RabbitMQConsumer] = None
        self.publisher: Optional[RabbitMQPublisher] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.running = False
        
        logger.info("summarization_service_initializing",
                   log_level=settings.log_level,
                   use_gpu=settings.use_gpu)
    
    def initialize(self):
        """Инициализация всех компонентов"""
        try:
            logger.info("initializing_components")
            
            # Инициализация NLP процессора
            logger.info("loading_nlp_models")
            self.nlp_processor = NLPProcessor()
            
            # Инициализация базы данных
            logger.info("connecting_to_database")
            self.db_manager = DatabaseManager()
            
            # Инициализация RabbitMQ publisher
            logger.info("initializing_rabbitmq_publisher")
            self.publisher = RabbitMQPublisher()
            self.publisher.connect()
            
            # Инициализация RabbitMQ consumer
            logger.info("initializing_rabbitmq_consumer")
            self.consumer = RabbitMQConsumer(callback=self.process_message)
            self.consumer.connect()
            
            logger.info("all_components_initialized")
            
        except Exception as e:
            logger.error("initialization_failed", error=str(e))
            raise
    
    def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Обработка входящего сообщения из RabbitMQ
        
        Args:
            message: Сообщение с сырым контентом
            
        Returns:
            True если обработка успешна, False иначе
        """
        try:
            message_type = message.get("message_type")
            
            if message_type != "raw_content":
                logger.warning("unexpected_message_type", message_type=message_type)
                return False
            
            # Извлечение данных
            platform = message.get("platform")
            source_id = message.get("source_id")
            source_url = message.get("source_url")
            content = message.get("content", {})
            
            text = content.get("text", "")
            author = content.get("author")
            published_at = content.get("published_at")
            original_url = content.get("original_url")
            
            if not text or not published_at:
                logger.warning("missing_required_fields",
                             has_text=bool(text),
                             has_published_at=bool(published_at))
                return False
            
            logger.info("processing_content",
                       platform=platform,
                       source_id=source_id,
                       text_length=len(text))
            
            # NLP обработка
            result = self.nlp_processor.process_content(text)
            
            if not result.get("success"):
                logger.error("nlp_processing_failed", source_id=source_id)
                return False
            
            # Сохранение в базу данных
            content_id = self.db_manager.save_processed_content(
                source_id=source_id,
                published_at=published_at,
                text=text,
                author=author,
                summary=result.get("summary", ""),
                embedding=result.get("embedding", []),
                sentiment=result.get("sentiment_score", 0.0),
                topic_tags=result.get("topics", [])
            )
            
            if not content_id:
                logger.error("database_save_failed", source_id=source_id)
                return False
            
            # Публикация обработанного контента
            success = self.publisher.publish_processed_content(
                content_id=content_id,
                source_id=source_id,
                platform=platform,
                summary=result.get("summary", ""),
                embedding=result.get("embedding", []),
                sentiment=result.get("sentiment_score", 0.0),
                sentiment_label=result.get("sentiment_label", "neutral"),
                topic_tags=result.get("topics", [])
            )
            
            if success:
                logger.info("content_processed_successfully",
                           content_id=content_id,
                           platform=platform,
                           summary_length=result.get("summary_length", 0),
                           sentiment=result.get("sentiment_label", "neutral"),
                           topics=result.get("topics", []))
                return True
            else:
                logger.error("publish_failed", content_id=content_id)
                return False
                
        except Exception as e:
            logger.error("message_processing_error",
                        error=str(e),
                        message_type=message.get("message_type"))
            
            # Публикация ошибки
            if self.publisher:
                self.publisher.publish_error(
                    service_name="summarization-service",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    original_message=message
                )
            
            return False
    
    def start(self):
        """Запуск сервиса"""
        try:
            logger.info("starting_summarization_service",
                       version="1.0.0",
                       models={
                           "summarization": settings.summarization_model,
                           "sentiment": settings.sentiment_model,
                           "embedding": settings.embedding_model
                       })
            
            self.running = True
            
            # Начало прослушивания очереди
            self.consumer.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("service_interrupted_by_user")
            self.stop()
        except Exception as e:
            logger.error("service_error", error=str(e))
            self.stop()
            raise
    
    def stop(self):
        """Остановка сервиса"""
        if not self.running:
            return
        
        logger.info("stopping_summarization_service")
        self.running = False
        
        try:
            # Остановка consumer
            if self.consumer:
                self.consumer.stop_consuming()
                self.consumer.close()
            
            # Закрытие publisher
            if self.publisher:
                self.publisher.close()
            
            # Закрытие БД
            if self.db_manager:
                self.db_manager.close()
            
            logger.info("summarization_service_stopped")
            
        except Exception as e:
            logger.error("stop_service_error", error=str(e))
    
    def handle_signal(self, signum, frame):
        """Обработка системных сигналов"""
        logger.info("signal_received", signal=signum)
        self.stop()
        sys.exit(0)


def main():
    """Точка входа приложения"""
    service = SummarizationService()
    
    # Регистрация обработчиков сигналов
    signal.signal(signal.SIGINT, service.handle_signal)
    signal.signal(signal.SIGTERM, service.handle_signal)
    
    try:
        # Инициализация
        service.initialize()
        
        # Запуск
        service.start()
        
    except Exception as e:
        logger.error("service_failed", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
