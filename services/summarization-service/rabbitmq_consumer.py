"""
RabbitMQ Consumer для получения сырого контента
"""

import pika
import json
import structlog
from typing import Callable, Optional
from config import settings

logger = structlog.get_logger()


class RabbitMQConsumer:
    """Consumer для получения сообщений из RabbitMQ"""
    
    def __init__(self, callback: Callable):
        """
        Инициализация consumer
        
        Args:
            callback: Функция обработки сообщений
        """
        self.callback = callback
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self.queue_name = "raw_content_queue"
        
        logger.info("rabbitmq_consumer_initialized",
                   queue=self.queue_name,
                   routing_key=settings.rabbitmq_input_routing_key)
    
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
            
            # Объявление очереди
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True,
                arguments={
                    'x-message-ttl': 86400000,  # 24 часа
                    'x-dead-letter-exchange': f"{settings.rabbitmq_exchange}.dlx",
                    'x-dead-letter-routing-key': f"{self.queue_name}.dlq"
                }
            )
            
            # Привязка очереди к exchange
            self.channel.queue_bind(
                exchange=settings.rabbitmq_exchange,
                queue=self.queue_name,
                routing_key=settings.rabbitmq_input_routing_key
            )
            
            # Настройка prefetch
            self.channel.basic_qos(prefetch_count=settings.prefetch_count)
            
            logger.info("rabbitmq_connected",
                       exchange=settings.rabbitmq_exchange,
                       queue=self.queue_name)
            
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise
    
    def start_consuming(self):
        """Начало прослушивания очереди"""
        try:
            logger.info("starting_consumer", queue=self.queue_name)
            
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self._on_message,
                auto_ack=False
            )
            
            logger.info("consumer_started", queue=self.queue_name)
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("consumer_interrupted")
            self.stop_consuming()
        except Exception as e:
            logger.error("consumer_error", error=str(e))
            raise
    
    def _on_message(self, ch, method, properties, body):
        """
        Обработка входящего сообщения
        
        Args:
            ch: Channel
            method: Method
            properties: Properties
            body: Тело сообщения
        """
        try:
            # Декодирование сообщения
            message_str = body.decode('utf-8')
            message_data = json.loads(message_str)
            
            logger.info("message_received",
                       routing_key=method.routing_key,
                       message_type=message_data.get("message_type"))
            
            # Вызов callback для обработки
            success = self.callback(message_data)
            
            if success:
                # Подтверждение обработки
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info("message_acknowledged", routing_key=method.routing_key)
            else:
                # Отклонение с возвратом в очередь
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                logger.warning("message_rejected", routing_key=method.routing_key)
                
        except json.JSONDecodeError as e:
            logger.error("message_decode_error", error=str(e))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error("message_processing_error", error=str(e))
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    def stop_consuming(self):
        """Остановка прослушивания"""
        try:
            if self.channel and self.channel.is_open:
                logger.info("stopping_consumer")
                self.channel.stop_consuming()
        except Exception as e:
            logger.error("stop_consuming_error", error=str(e))
    
    def close(self):
        """Закрытие соединения"""
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
            logger.info("rabbitmq_connection_closed")
        except Exception as e:
            logger.error("close_connection_error", error=str(e))
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
