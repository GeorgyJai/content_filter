"""
Конфигурация Ranking Service
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Конфигурация сервиса ранжирования"""
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "content_filter_db")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    
    # gRPC Server
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50053"))
    
    # Model Configuration
    MODEL_NAME: str = os.getenv("MODEL_NAME", "DeepPavlov/rubert-base-cased")
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "768"))
    MAX_LENGTH: int = int(os.getenv("MAX_LENGTH", "512"))
    
    # Ranking Configuration
    DEFAULT_LIMIT: int = int(os.getenv("DEFAULT_LIMIT", "10"))
    MIN_SIMILARITY: float = float(os.getenv("MIN_SIMILARITY", "0.5"))
    
    # Feedback Learning
    FEEDBACK_WEIGHT: float = float(os.getenv("FEEDBACK_WEIGHT", "0.3"))
    RELEVANT_BOOST: float = float(os.getenv("RELEVANT_BOOST", "1.0"))
    NOT_RELEVANT_PENALTY: float = float(os.getenv("NOT_RELEVANT_PENALTY", "-0.5"))
    
    @property
    def database_url(self) -> str:
        """Получить URL подключения к базе данных"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


# Глобальный экземпляр конфигурации
config = Config()
