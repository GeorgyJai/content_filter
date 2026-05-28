"""Configuration for VK Collector Service."""
import os
from typing import Optional


class Config:
    """VK Collector configuration."""
    
    # VK API Configuration
    VK_API_VERSION: str = os.getenv("VK_API_VERSION", "5.131")
    VK_CONFIRMATION_TOKEN: str = os.getenv("VK_CONFIRMATION_TOKEN", "")
    VK_SECRET_KEY: str = os.getenv("VK_SECRET_KEY", "")
    VK_ACCESS_TOKEN: str = os.getenv("VK_ACCESS_TOKEN", "")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_EXCHANGE: str = os.getenv("RABBITMQ_EXCHANGE", "content_exchange")
    RABBITMQ_ROUTING_KEY: str = os.getenv("RABBITMQ_ROUTING_KEY", "raw.vk")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_rabbitmq_url(cls) -> str:
        """Get RabbitMQ connection URL."""
        return f"amqp://{cls.RABBITMQ_USER}:{cls.RABBITMQ_PASSWORD}@{cls.RABBITMQ_HOST}:{cls.RABBITMQ_PORT}/"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        required = [
            cls.VK_CONFIRMATION_TOKEN,
            cls.VK_SECRET_KEY,
        ]
        return all(required)


config = Config()
