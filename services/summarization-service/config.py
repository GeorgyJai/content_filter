"""
Конфигурация Summarization Service
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Настройки сервиса суммаризации"""
    
    # RabbitMQ настройки
    rabbitmq_host: str = Field(default="rabbitmq", description="RabbitMQ host")
    rabbitmq_port: int = Field(default=5672, description="RabbitMQ port")
    rabbitmq_user: str = Field(default="admin", description="RabbitMQ username")
    rabbitmq_password: str = Field(default="admin_password", description="RabbitMQ password")
    rabbitmq_exchange: str = Field(default="content_exchange", description="RabbitMQ exchange name")
    rabbitmq_input_routing_key: str = Field(default="raw.*", description="Routing key для входящих сообщений")
    rabbitmq_output_routing_key_prefix: str = Field(default="processed", description="Префикс routing key для исходящих")
    
    # PostgreSQL настройки
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="content_filter_db", description="Database name")
    postgres_user: str = Field(default="postgres", description="Database user")
    postgres_password: str = Field(default="postgres_password", description="Database password")
    
    # NLP модели настройки
    summarization_model: str = Field(
        default="IlyaGusev/mbart_ru_sum_gazeta",
        description="Модель для суммаризации"
    )
    sentiment_model: str = Field(
        default="blanchefort/rubert-base-cased-sentiment",
        description="Модель для анализа тональности"
    )
    embedding_model: str = Field(
        default="DeepPavlov/rubert-base-cased",
        description="Модель для генерации эмбеддингов"
    )
    
    # Параметры суммаризации
    default_max_length: int = Field(default=150, description="Максимальная длина резюме (слова)")
    default_min_length: int = Field(default=50, description="Минимальная длина резюме (слова)")
    num_beams: int = Field(default=4, description="Количество beams для генерации")
    length_penalty: float = Field(default=2.0, description="Штраф за длину")
    
    # Адаптивная суммаризация
    very_interested_length: int = Field(default=250, description="Длина для очень интересного контента")
    interested_length: int = Field(default=150, description="Длина для интересного контента")
    maybe_length: int = Field(default=75, description="Длина для возможно интересного")
    not_interested_length: int = Field(default=30, description="Длина для неинтересного")
    
    # Параметры обработки
    batch_size: int = Field(default=1, description="Размер батча для обработки")
    prefetch_count: int = Field(default=1, description="Количество prefetch сообщений из RabbitMQ")
    max_text_length: int = Field(default=2000, description="Максимальная длина текста для обработки (слова)")
    
    # Логирование
    log_level: str = Field(default="INFO", description="Уровень логирования")
    
    # Производительность
    use_gpu: bool = Field(default=False, description="Использовать GPU если доступен")
    model_cache_dir: Optional[str] = Field(default="./models", description="Директория для кэша моделей")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def rabbitmq_url(self) -> str:
        """Полный URL для подключения к RabbitMQ"""
        return f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}@{self.rabbitmq_host}:{self.rabbitmq_port}/"
    
    @property
    def database_url(self) -> str:
        """Полный URL для подключения к PostgreSQL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


# Глобальный экземпляр настроек
settings = Settings()
