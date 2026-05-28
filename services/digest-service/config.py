"""
Конфигурация Digest Service
"""

import os
from typing import Optional


class Config:
    """Конфигурация сервиса генерации дайджестов"""
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "content_filter_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres_password")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # gRPC
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50052"))
    GRPC_MAX_WORKERS: int = int(os.getenv("GRPC_MAX_WORKERS", "10"))
    
    # User Service
    USER_SERVICE_HOST: str = os.getenv("USER_SERVICE_HOST", "localhost")
    USER_SERVICE_PORT: int = int(os.getenv("USER_SERVICE_PORT", "50051"))
    
    # Ranking Service
    RANKING_SERVICE_HOST: str = os.getenv("RANKING_SERVICE_HOST", "localhost")
    RANKING_SERVICE_PORT: int = int(os.getenv("RANKING_SERVICE_PORT", "50053"))
    
    # Scheduler
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    SCHEDULER_CHECK_INTERVAL: int = int(os.getenv("SCHEDULER_CHECK_INTERVAL", "60"))  # секунды
    
    # Digest settings
    DEFAULT_DIGEST_INTERVAL_HOURS: int = int(os.getenv("DEFAULT_DIGEST_INTERVAL_HOURS", "8"))
    DEFAULT_MAX_ITEMS: int = int(os.getenv("DEFAULT_MAX_ITEMS", "10"))
    MIN_CONTENT_AGE_MINUTES: int = int(os.getenv("MIN_CONTENT_AGE_MINUTES", "5"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Bot Service (для отправки дайджестов)
    BOT_SERVICE_HOST: str = os.getenv("BOT_SERVICE_HOST", "localhost")
    BOT_SERVICE_PORT: int = int(os.getenv("BOT_SERVICE_PORT", "50054"))


config = Config()
