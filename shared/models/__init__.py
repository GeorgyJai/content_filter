"""
Shared models package
Содержит общие модели данных и схемы сообщений
"""

from .message_schemas import (
    RawContentMessage,
    ProcessedContentMessage,
    SummarizationTaskMessage,
    RankingTaskMessage,
    DigestGenerationMessage,
    ProfileUpdateMessage,
    ErrorMessage,
    ContentData,
    validate_message,
    serialize_message,
    MESSAGE_TYPE_MAP,
)

__all__ = [
    "RawContentMessage",
    "ProcessedContentMessage",
    "SummarizationTaskMessage",
    "RankingTaskMessage",
    "DigestGenerationMessage",
    "ProfileUpdateMessage",
    "ErrorMessage",
    "ContentData",
    "validate_message",
    "serialize_message",
    "MESSAGE_TYPE_MAP",
]
