"""
RabbitMQ Publisher для отправки обработанного контента
"""

import pika
import json
from datetime import datetime
from typing import Dict, Any, Optional
import structlog
from config import settings

logger = structlog.get_logger()


class RabbitMQPublisher:
    """Publisher для отправки обработанных сообщений в RabbitMQ"""
    
    def __init__(self):
        """Инициализация publisher"""
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        
        logger.info("rabbitmq_publisher_initialized",
                   exchange=settings.rabbitmq_exchange)
    
    def connect(self):
        """Установка соединения с RabbitMQ"""
        try:
            logger.info("connecting_to_rabbitmq",
                       host=settings.rabbitmq_host,
                       port=settings.rabbitmq_port)
            
            credentials = pika.PlainCredentials(
                settings.rabbitmq_user,
                settings.rabbitmq_password
            )
            
            parameters = pika.ConnectionParameters(
                host=settings.rabbitmq_host,
                port=settings.rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Объявление exchange
            self.channel.exchange_declare(
                exchange=settings.rabbitmq_exchange,
                exchange_type='topic',
                durable=True
            )
            
            logger.info("rabbitmq_publisher_connected",
                       exchange=settings.rabbitmq_exchange)
            
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise
    
    def publish_processed_content(
        self,
        content_id: int,
        source_id: int,
        platform: str,
        summary: str,
        embedding: list,
        sentiment: float,
        sentiment_label: str,
        topic_tags: list
    ) -> bool:
        """
        Публикация обработанного контента
        
        Args:
            content_id: ID контента в БД
            source_id: ID источника
            platform: Платформа (telegram, vk, youtube)
            summary: Краткое содержание
            embedding: Векторное представление
            sentiment: Тональность (-1 до 1)
            sentiment_label: Метка тональности
            topic_tags: Список тем/тегов
            
        Returns:
            True если успешно, False иначе
        """
        try:
            # Формирование сообщения
            message = {
                "message_type": "processed_content",
                "content_id": content_id,
                "source_id": source_id,
                "platform": platform,
                "summary": summary,
                "embedding": embedding,
                "sentiment": sentiment,
                "sentiment_label": sentiment_label,
                "topic_tags": topic_tags,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Routing key: processed.{platform}
            routing_key = f"{settings.rabbitmq_output_routing_key_prefix}.{platform}"
            
            # Публикация
            self.channel.basic_publish(
                exchange=settings.rabbitmq_exchange,
                routing_key=routing_key,
                body=json.dumps(message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json',
                    content_encoding='utf-8'
                )
            )
            
            logger.info("processed_content_published",
                       content_id=content_id,
                       routing_key=routing_key,
                       platform=platform)
            
            return True
            
        except Exception as e:
            logger.error("publish_failed",
                        content_id=content_id,
                        error=str(e))
            return False
    
    def publish_error(
        self,
        service_name: str,
        error_type: str,
        error_message: str,
        original_message: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Публикация сообщения об ошибке
        
        Args:
            service_name: Имя сервиса
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
            original_message: Оригинальное сообщение
            
        Returns:
            True если успешно, False иначе
        """
        try:
            message = {
                "message_type": "error",
                "service_name": service_name,
                "error_type": error_type,
                "error_message": error_message,
                "original_message": original_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            routing_key = f"error.{service_name}"
            
            self.channel.basic_publish(
                exchange="error_exchange",
                routing_key=routing_key,
                body=json.dumps(message, ensure_ascii=False),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            
            logger.info("error_published",
                       error_type=error_type,
                       routing_key=routing_key)
            
            return True
            
        except Exception as e:
            logger.error("error_publish_failed", error=str(e))
            return False
    
    def close(self):
        """Закрытие соединения"""
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
            logger.info("rabbitmq_publisher_closed")
        except Exception as e:
            logger.error("close_connection_error", error=str(e))
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
