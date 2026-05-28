"""
Модуль для работы с базой данных PostgreSQL
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from config import settings

logger = structlog.get_logger()

Base = declarative_base()


class ContentUnit(Base):
    """Модель единицы контента"""
    __tablename__ = 'content_units'
    
    content_id = Column(Integer, primary_key=True)
    source_id = Column(Integer, nullable=False)
    published_at = Column(TIMESTAMP, nullable=False)
    text = Column(Text)
    author = Column(String(255))
    topic_tags = Column(JSON)
    sentiment = Column(Float)
    relevance_score = Column(Float)
    embedding = Column(Vector(768))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self):
        """Инициализация подключения к БД"""
        try:
            logger.info("initializing_database_connection",
                       host=settings.postgres_host,
                       database=settings.postgres_db)
            
            self.engine = create_engine(
                settings.database_url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("database_connection_initialized")
            
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise
    
    def save_processed_content(
        self,
        source_id: int,
        published_at: str,
        text: str,
        author: Optional[str],
        summary: str,
        embedding: list,
        sentiment: float,
        topic_tags: list
    ) -> Optional[int]:
        """
        Сохранение обработанного контента в БД
        
        Args:
            source_id: ID источника
            published_at: Дата публикации
            text: Оригинальный текст
            author: Автор
            summary: Краткое содержание
            embedding: Векторное представление
            sentiment: Тональность
            topic_tags: Теги/темы
            
        Returns:
            ID созданной записи или None при ошибке
        """
        session = self.SessionLocal()
        try:
            # Преобразование даты
            published_datetime = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            
            # Создание записи
            content = ContentUnit(
                source_id=source_id,
                published_at=published_datetime,
                text=text,
                author=author,
                topic_tags=topic_tags,
                sentiment=sentiment,
                embedding=embedding
            )
            
            session.add(content)
            session.commit()
            session.refresh(content)
            
            content_id = content.content_id
            
            logger.info("content_saved_to_database",
                       content_id=content_id,
                       source_id=source_id)
            
            return content_id
            
        except Exception as e:
            session.rollback()
            logger.error("save_content_failed", error=str(e))
            return None
        finally:
            session.close()
    
    def get_content_by_id(self, content_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение контента по ID
        
        Args:
            content_id: ID контента
            
        Returns:
            Словарь с данными контента или None
        """
        session = self.SessionLocal()
        try:
            content = session.query(ContentUnit).filter(
                ContentUnit.content_id == content_id
            ).first()
            
            if content:
                return {
                    "content_id": content.content_id,
                    "source_id": content.source_id,
                    "published_at": content.published_at.isoformat(),
                    "text": content.text,
                    "author": content.author,
                    "topic_tags": content.topic_tags,
                    "sentiment": content.sentiment,
                    "embedding": content.embedding
                }
            
            return None
            
        except Exception as e:
            logger.error("get_content_failed", content_id=content_id, error=str(e))
            return None
        finally:
            session.close()
    
    def close(self):
        """Закрытие соединения с БД"""
        try:
            self.engine.dispose()
            logger.info("database_connection_closed")
        except Exception as e:
            logger.error("close_database_error", error=str(e))
