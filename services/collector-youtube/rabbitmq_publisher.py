"""RabbitMQ publisher for YouTube content."""
import json
import pika
import structlog
from typing import Dict, Any, Optional
from config import config

logger = structlog.get_logger()


class RabbitMQPublisher:
    """Publisher for sending YouTube content to RabbitMQ."""
    
    def __init__(self):
        """Initialize RabbitMQ publisher."""
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            parameters = pika.ConnectionParameters(
                host=config.RABBITMQ_HOST,
                port=config.RABBITMQ_PORT,
                credentials=pika.PlainCredentials(
                    config.RABBITMQ_USER,
                    config.RABBITMQ_PASSWORD
                ),
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=config.RABBITMQ_EXCHANGE,
                exchange_type='topic',
                durable=True
            )
            
            logger.info(
                "rabbitmq_connected",
                host=config.RABBITMQ_HOST,
                exchange=config.RABBITMQ_EXCHANGE
            )
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise
    
    def publish(self, message: Dict[str, Any]) -> bool:
        """
        Publish message to RabbitMQ.
        
        Args:
            message: Message data to publish
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            if not self.connection or self.connection.is_closed:
                self._connect()
            
            body = json.dumps(message, ensure_ascii=False)
            
            self.channel.basic_publish(
                exchange=config.RABBITMQ_EXCHANGE,
                routing_key=config.RABBITMQ_ROUTING_KEY,
                body=body.encode('utf-8'),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json',
                    content_encoding='utf-8'
                )
            )
            
            logger.info(
                "message_published",
                routing_key=config.RABBITMQ_ROUTING_KEY,
                video_id=message.get('content', {}).get('video_id')
            )
            return True
            
        except Exception as e:
            logger.error("publish_failed", error=str(e), message=message)
            return False
    
    def close(self) -> None:
        """Close RabbitMQ connection."""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("rabbitmq_connection_closed")
        except Exception as e:
            logger.error("close_connection_failed", error=str(e))
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
