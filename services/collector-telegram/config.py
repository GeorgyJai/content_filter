"""
Конфигурация Telegram Collector Service
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки сервиса"""
    
    # Telegram API credentials
    telegram_api_id: int = Field(..., description="Telegram API ID")
    telegram_api_hash: str = Field(..., description="Telegram API Hash")
    telegram_phone: str = Field(default="", description="Номер телефона для авторизации (опционально)")
    telegram_session_name: str = Field(default="collector_session", description="Имя сессии Telethon")
    
    # RabbitMQ
    rabbitmq_host: str = Field(default="localhost", description="RabbitMQ host")
    rabbitmq_port: int = Field(default=5672, description="RabbitMQ port")
    rabbitmq_user: str = Field(default="admin", description="RabbitMQ username")
    rabbitmq_password: str = Field(default="admin_password", description="RabbitMQ password")
    rabbitmq_exchange: str = Field(default="content_exchange", description="RabbitMQ exchange name")
    rabbitmq_routing_key: str = Field(default="raw.telegram", description="Routing key для Telegram контента")
    
    # PostgreSQL (для получения списка источников)
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="content_filter_db", description="Database name")
    postgres_user: str = Field(default="postgres", description="Database user")
    postgres_password: str = Field(default="postgres", description="Database password")
    
    # Service settings
    log_level: str = Field(default="INFO", description="Logging level")
    poll_interval: int = Field(default=60, description="Интервал опроса каналов в секундах")
    max_messages_per_channel: int = Field(default=50, description="Максимум сообщений за один опрос")
    
    @property
    def rabbitmq_url(self) -> str:
        """Формирование URL для подключения к RabbitMQ"""
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"
    
    @property
    def database_url(self) -> str:
        """Формирование URL для подключения к PostgreSQL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Глобальный экземпляр настроек
settings = Settings()
