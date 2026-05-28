"""
Схемы сообщений для RabbitMQ
Определяет форматы сообщений, передаваемых между сервисами через RabbitMQ
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


# ============================================
# Сообщения для сырого контента (Raw Content)
# ============================================

class RawContentMessage(BaseModel):
    """
    Сообщение с сырым контентом из коллекторов
    Routing key: raw.{platform} (например: raw.telegram, raw.vk, raw.youtube)
    Exchange: content_exchange (topic)
    Queue: raw_content_queue
    """
    message_type: str = Field(default="raw_content", const=True)
    platform: str = Field(..., description="Платформа источника: telegram, vk, youtube")
    source_id: Optional[int] = Field(None, description="ID источника в БД (если известен)")
    source_url: str = Field(..., description="URL источника")
    content: Dict[str, Any] = Field(..., description="Данные контента")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "raw_content",
                "platform": "telegram",
                "source_id": 123,
                "source_url": "https://t.me/channel_name",
                "content": {
                    "text": "Текст публикации",
                    "author": "Автор канала",
                    "published_at": "2026-05-27T10:00:00Z",
                    "media_urls": ["https://example.com/image.jpg"],
                    "original_url": "https://t.me/channel_name/12345"
                },
                "timestamp": "2026-05-27T10:00:05Z"
            }
        }


class ContentData(BaseModel):
    """Структура данных контента"""
    text: str = Field(..., description="Текст публикации")
    author: Optional[str] = Field(None, description="Автор публикации")
    published_at: str = Field(..., description="Дата публикации (ISO 8601)")
    media_urls: List[str] = Field(default_factory=list, description="Ссылки на медиа")
    original_url: str = Field(..., description="Ссылка на оригинал")
    
    @validator('published_at')
    def validate_datetime(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('published_at must be valid ISO 8601 datetime')


# ============================================
# Сообщения для обработанного контента (Processed Content)
# ============================================

class ProcessedContentMessage(BaseModel):
    """
    Сообщение с обработанным контентом после NLP-обработки
    Routing key: processed.{platform}
    Exchange: content_exchange (topic)
    Queue: processed_content_queue
    """
    message_type: str = Field(default="processed_content", const=True)
    content_id: int = Field(..., description="ID контента в БД")
    source_id: int = Field(..., description="ID источника в БД")
    platform: str = Field(..., description="Платформа источника")
    summary: str = Field(..., description="Краткое содержание")
    embedding: List[float] = Field(..., description="Векторное представление (768 измерений)")
    sentiment: float = Field(..., description="Тональность от -1 до 1")
    sentiment_label: str = Field(..., description="Метка тональности: negative, neutral, positive")
    topic_tags: List[str] = Field(default_factory=list, description="Извлеченные темы/теги")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @validator('embedding')
    def validate_embedding_dimension(cls, v):
        if len(v) != 768:
            raise ValueError('embedding must have exactly 768 dimensions')
        return v
    
    @validator('sentiment')
    def validate_sentiment_range(cls, v):
        if not -1 <= v <= 1:
            raise ValueError('sentiment must be between -1 and 1')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "processed_content",
                "content_id": 456,
                "source_id": 123,
                "platform": "telegram",
                "summary": "Краткое содержание публикации о новых технологиях",
                "embedding": [0.1, 0.2, 0.3],  # ... 768 значений
                "sentiment": 0.75,
                "sentiment_label": "positive",
                "topic_tags": ["технологии", "AI", "инновации"],
                "timestamp": "2026-05-27T10:01:00Z"
            }
        }


# ============================================
# Сообщения для задач суммаризации (Summarization Tasks)
# ============================================

class SummarizationTaskMessage(BaseModel):
    """
    Задача на суммаризацию текста
    Routing key: task.summarization
    Exchange: task_exchange (topic)
    Queue: summarization_task_queue
    """
    message_type: str = Field(default="summarization_task", const=True)
    content_id: int = Field(..., description="ID контента в БД")
    text: str = Field(..., description="Текст для суммаризации")
    interest_level: Optional[str] = Field(None, description="Уровень интереса для адаптивной суммаризации")
    max_length: Optional[int] = Field(150, description="Максимальная длина резюме")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "summarization_task",
                "content_id": 456,
                "text": "Длинный текст публикации...",
                "interest_level": "interested",
                "max_length": 150,
                "timestamp": "2026-05-27T10:00:30Z"
            }
        }


# ============================================
# Сообщения для задач ранжирования (Ranking Tasks)
# ============================================

class RankingTaskMessage(BaseModel):
    """
    Задача на ранжирование контента для пользователя
    Routing key: task.ranking
    Exchange: task_exchange (topic)
    Queue: ranking_task_queue
    """
    message_type: str = Field(default="ranking_task", const=True)
    user_id: int = Field(..., description="ID пользователя")
    content_ids: List[int] = Field(..., description="Список ID контента для ранжирования")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "ranking_task",
                "user_id": 1,
                "content_ids": [456, 457, 458, 459, 460],
                "timestamp": "2026-05-27T10:02:00Z"
            }
        }


# ============================================
# Сообщения для генерации дайджестов (Digest Generation)
# ============================================

class DigestGenerationMessage(BaseModel):
    """
    Задача на генерацию дайджеста
    Routing key: task.digest
    Exchange: task_exchange (topic)
    Queue: digest_generation_queue
    """
    message_type: str = Field(default="digest_generation", const=True)
    user_id: int = Field(..., description="ID пользователя")
    period_start: str = Field(..., description="Начало периода (ISO 8601)")
    period_end: str = Field(..., description="Конец периода (ISO 8601)")
    max_items: int = Field(10, description="Максимальное количество элементов")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    @validator('period_start', 'period_end')
    def validate_datetime(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError('period must be valid ISO 8601 datetime')
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "digest_generation",
                "user_id": 1,
                "period_start": "2026-05-27T00:00:00Z",
                "period_end": "2026-05-27T23:59:59Z",
                "max_items": 10,
                "timestamp": "2026-05-27T10:03:00Z"
            }
        }


# ============================================
# Сообщения для обновления профиля (Profile Update)
# ============================================

class ProfileUpdateMessage(BaseModel):
    """
    Сообщение об обновлении профиля пользователя
    Routing key: event.profile_update
    Exchange: event_exchange (topic)
    Queue: profile_update_queue
    """
    message_type: str = Field(default="profile_update", const=True)
    user_id: int = Field(..., description="ID пользователя")
    update_type: str = Field(..., description="Тип обновления: feedback, preferences, subscription")
    data: Dict[str, Any] = Field(..., description="Данные обновления")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "profile_update",
                "user_id": 1,
                "update_type": "feedback",
                "data": {
                    "content_id": 456,
                    "reaction": "relevant"
                },
                "timestamp": "2026-05-27T10:04:00Z"
            }
        }


# ============================================
# Сообщения об ошибках (Error Messages)
# ============================================

class ErrorMessage(BaseModel):
    """
    Сообщение об ошибке обработки
    Routing key: error.{service_name}
    Exchange: error_exchange (topic)
    Queue: error_queue
    """
    message_type: str = Field(default="error", const=True)
    service_name: str = Field(..., description="Имя сервиса, где произошла ошибка")
    error_type: str = Field(..., description="Тип ошибки")
    error_message: str = Field(..., description="Сообщение об ошибке")
    original_message: Optional[Dict[str, Any]] = Field(None, description="Оригинальное сообщение")
    stack_trace: Optional[str] = Field(None, description="Stack trace ошибки")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "message_type": "error",
                "service_name": "summarization-service",
                "error_type": "ModelError",
                "error_message": "Failed to generate summary",
                "original_message": {"content_id": 456},
                "stack_trace": "Traceback...",
                "timestamp": "2026-05-27T10:05:00Z"
            }
        }


# ============================================
# Утилиты для валидации
# ============================================

MESSAGE_TYPE_MAP = {
    "raw_content": RawContentMessage,
    "processed_content": ProcessedContentMessage,
    "summarization_task": SummarizationTaskMessage,
    "ranking_task": RankingTaskMessage,
    "digest_generation": DigestGenerationMessage,
    "profile_update": ProfileUpdateMessage,
    "error": ErrorMessage,
}


def validate_message(message_dict: Dict[str, Any]) -> BaseModel:
    """
    Валидация сообщения на основе message_type
    
    Args:
        message_dict: Словарь с данными сообщения
        
    Returns:
        Валидированный объект Pydantic модели
        
    Raises:
        ValueError: Если message_type неизвестен или валидация не прошла
    """
    message_type = message_dict.get("message_type")
    
    if message_type not in MESSAGE_TYPE_MAP:
        raise ValueError(f"Unknown message_type: {message_type}")
    
    model_class = MESSAGE_TYPE_MAP[message_type]
    return model_class(**message_dict)


def serialize_message(message: BaseModel) -> Dict[str, Any]:
    """
    Сериализация сообщения в словарь для отправки в RabbitMQ
    
    Args:
        message: Объект Pydantic модели
        
    Returns:
        Словарь с данными сообщения
    """
    return message.dict(exclude_none=True)
