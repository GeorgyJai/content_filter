"""Configuration for YouTube Collector Service."""
import os
from typing import Optional


class Config:
    """YouTube Collector configuration."""
    
    # YouTube API Configuration
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_API_VERSION: str = os.getenv("YOUTUBE_API_VERSION", "v3")
    
    # Polling Configuration
    POLL_INTERVAL_SECONDS: int = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))  # 5 minutes default
    MAX_RESULTS_PER_CHANNEL: int = int(os.getenv("MAX_RESULTS_PER_CHANNEL", "10"))
    
    # Transcription Configuration
    ENABLE_TRANSCRIPTION: bool = os.getenv("ENABLE_TRANSCRIPTION", "false").lower() == "true"
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
    TRANSCRIPTION_LANGUAGE: str = os.getenv("TRANSCRIPTION_LANGUAGE", "ru")
    
    # Download Configuration
    TEMP_DOWNLOAD_DIR: str = os.getenv("TEMP_DOWNLOAD_DIR", "/tmp/youtube_downloads")
    MAX_VIDEO_DURATION_MINUTES: int = int(os.getenv("MAX_VIDEO_DURATION_MINUTES", "60"))
    
    # RabbitMQ Configuration
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD: str = os.getenv("RABBITMQ_PASSWORD", "guest")
    RABBITMQ_EXCHANGE: str = os.getenv("RABBITMQ_EXCHANGE", "content_exchange")
    RABBITMQ_ROUTING_KEY: str = os.getenv("RABBITMQ_ROUTING_KEY", "raw.youtube")
    
    # Database Configuration (for tracking processed videos)
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "content_filter_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_rabbitmq_url(cls) -> str:
        """Get RabbitMQ connection URL."""
        return f"amqp://{cls.RABBITMQ_USER}:{cls.RABBITMQ_PASSWORD}@{cls.RABBITMQ_HOST}:{cls.RABBITMQ_PORT}/"
    
    @classmethod
    def get_postgres_url(cls) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration."""
        if not cls.YOUTUBE_API_KEY:
            return False
        return True


config = Config()
