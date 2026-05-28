"""
RabbitMQ Publisher для отправки собранного контента
"""

import json
import pika
import structlog
from typing import Dict, Any
from datetime import datetime

from config import settings


logger = structlog.get_logger(__name__)


class RabbitMQPublisher:
    """Класс для публикации сообщений в RabbitMQ"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = settings.rabbitmq_exchange
        self.routing_key = settings.rabbitmq_routing_key
        
    def connect(self):
        """Установка соединения с RabbitMQ"""
        try:
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
            
            # Объявление exchange (если не существует)
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type='topic',
                durable=True
            )
            
            logger.info(
                "rabbitmq_connected",
                host=settings.rabbitmq_host,
                exchange=self.exchange
            )
            
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise
    
    def publish_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Публикация сообщения в RabbitMQ
        
        Args:
            message_data: Данные сообщения для публикации
            
        Returns:
            bool: True если успешно, False в случае ошибки
        """
        try:
            # Проверка соединения
            if not self.connection or self.connection.is_closed:
                self.connect()
            
            # Добавление timestamp если отсутствует
            if 'timestamp' not in message_data:
                message_data['timestamp'] = datetime.utcnow().isoformat()
            
            # Сериализация в JSON
            message_body = json.dumps(message_data, ensure_ascii=False)
            
            # Публикация сообщения
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=message_body.encode('utf-8'),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent message
                    content_type='application/json',
                    content_encoding='utf-8'
                )
            )
            
            logger.info(
                "message_published",
                routing_key=self.routing_key,
                source_url=message_data.get('source_url', 'unknown')
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "message_publish_failed",
                error=str(e),
                message_data=message_data
            )
            return False
    
    def close(self):
        """Закрытие соединения с RabbitMQ"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("rabbitmq_connection_closed")
        except Exception as e:
            logger.error("rabbitmq_close_error", error=str(e))
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
