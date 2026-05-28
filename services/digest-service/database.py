"""
Модуль для работы с базой данных
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, Text, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import Vector

from config import config

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================
# Модели базы данных
# ============================================

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    telegram_id = Column(String(100), unique=True, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class UserProfile(Base):
    """Профиль пользователя с предпочтениями"""
    __tablename__ = 'user_profiles'
    
    profile_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    preferences = Column(JSON)
    interests_embedding = Column(Vector(768))
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class ContentSource(Base):
    """Источник контента"""
    __tablename__ = 'content_sources'
    
    source_id = Column(Integer, primary_key=True)
    platform_type = Column(String(50), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    topic = Column(String(255))
    publish_frequency = Column(String(50))


class Subscription(Base):
    """Подписка пользователя на источник"""
    __tablename__ = 'subscriptions'
    
    subscription_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    source_id = Column(Integer, ForeignKey('content_sources.source_id'), nullable=False)
    subscribed_at = Column(TIMESTAMP, default=datetime.utcnow)


class ContentUnit(Base):
    """Единица контента"""
    __tablename__ = 'content_units'
    
    content_id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('content_sources.source_id'), nullable=False)
    published_at = Column(TIMESTAMP, nullable=False)
    text = Column(Text)
    summary = Column(Text)
    author = Column(String(255))
    topic_tags = Column(JSON)
    sentiment = Column(Float)
    relevance_score = Column(Float)
    embedding = Column(Vector(768))
    original_url = Column(String(500))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class Digest(Base):
    """Дайджест"""
    __tablename__ = 'digests'
    
    digest_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    period_start = Column(TIMESTAMP, nullable=False)
    period_end = Column(TIMESTAMP, nullable=False)
    telegram_message_id = Column(String(100))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    items = relationship("DigestItem", back_populates="digest", cascade="all, delete-orphan")


class DigestItem(Base):
    """Элемент дайджеста"""
    __tablename__ = 'digest_items'
    
    item_id = Column(Integer, primary_key=True)
    digest_id = Column(Integer, ForeignKey('digests.digest_id'), nullable=False)
    content_id = Column(Integer, ForeignKey('content_units.content_id'), nullable=False)
    annotation = Column(Text)
    rank = Column(Integer)
    
    digest = relationship("Digest", back_populates="items")
    content = relationship("ContentUnit")


class Feedback(Base):
    """Обратная связь пользователя"""
    __tablename__ = 'feedback'
    
    feedback_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content_id = Column(Integer, ForeignKey('content_units.content_id'), nullable=False)
    reaction = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


# ============================================
# Database Manager
# ============================================

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self):
        self.engine = create_engine(
            config.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database connection established: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    
    def get_session(self) -> Session:
        """Получить сессию БД"""
        return self.SessionLocal()
    
    def get_users_for_digest(self, session: Session) -> List[Dict[str, Any]]:
        """
        Получить пользователей, которым нужно отправить дайджест
        
        Returns:
            Список словарей с информацией о пользователях
        """
        try:
            # Получаем всех пользователей с их настройками
            users = session.query(User, UserProfile).join(
                UserProfile, User.user_id == UserProfile.user_id
            ).all()
            
            result = []
            current_time = datetime.utcnow()
            
            for user, profile in users:
                # Получаем настройки интервала из preferences
                preferences = profile.preferences or {}
                interval_hours = preferences.get('digest_interval_hours', config.DEFAULT_DIGEST_INTERVAL_HOURS)
                
                # Получаем последний дайджест пользователя
                last_digest = session.query(Digest).filter(
                    Digest.user_id == user.user_id
                ).order_by(Digest.created_at.desc()).first()
                
                # Проверяем, нужно ли отправлять дайджест
                should_send = False
                if last_digest is None:
                    should_send = True
                else:
                    time_since_last = current_time - last_digest.created_at
                    if time_since_last >= timedelta(hours=interval_hours):
                        should_send = True
                
                if should_send:
                    result.append({
                        'user_id': user.user_id,
                        'telegram_id': user.telegram_id,
                        'interval_hours': interval_hours,
                        'last_digest_at': last_digest.created_at if last_digest else None
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting users for digest: {e}")
            return []
    
    def get_user_subscriptions(self, session: Session, user_id: int) -> List[int]:
        """Получить ID источников, на которые подписан пользователь"""
        try:
            subscriptions = session.query(Subscription.source_id).filter(
                Subscription.user_id == user_id
            ).all()
            return [sub.source_id for sub in subscriptions]
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return []
    
    def get_new_content(
        self,
        session: Session,
        source_ids: List[int],
        since: datetime,
        limit: int = 100
    ) -> List[ContentUnit]:
        """
        Получить новый контент из указанных источников
        
        Args:
            session: Сессия БД
            source_ids: Список ID источников
            since: Получить контент после этой даты
            limit: Максимальное количество элементов
            
        Returns:
            Список объектов ContentUnit
        """
        try:
            if not source_ids:
                return []
            
            content = session.query(ContentUnit).filter(
                ContentUnit.source_id.in_(source_ids),
                ContentUnit.created_at >= since,
                ContentUnit.summary.isnot(None),
                ContentUnit.embedding.isnot(None)
            ).order_by(ContentUnit.published_at.desc()).limit(limit).all()
            
            return content
        except Exception as e:
            logger.error(f"Error getting new content: {e}")
            return []
    
    def save_digest(
        self,
        session: Session,
        user_id: int,
        period_start: datetime,
        period_end: datetime,
        items: List[Dict[str, Any]],
        telegram_message_id: Optional[str] = None
    ) -> Optional[int]:
        """
        Сохранить дайджест в БД
        
        Args:
            session: Сессия БД
            user_id: ID пользователя
            period_start: Начало периода
            period_end: Конец периода
            items: Список элементов дайджеста
            telegram_message_id: ID сообщения в Telegram
            
        Returns:
            ID созданного дайджеста или None при ошибке
        """
        try:
            # Создаем дайджест
            digest = Digest(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                telegram_message_id=telegram_message_id
            )
            session.add(digest)
            session.flush()
            
            # Добавляем элементы дайджеста
            for idx, item in enumerate(items, 1):
                digest_item = DigestItem(
                    digest_id=digest.digest_id,
                    content_id=item['content_id'],
                    annotation=item['annotation'],
                    rank=idx
                )
                session.add(digest_item)
            
            session.commit()
            logger.info(f"Digest saved: digest_id={digest.digest_id}, user_id={user_id}, items={len(items)}")
            return digest.digest_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving digest: {e}")
            return None
    
    def get_digest(self, session: Session, digest_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить дайджест по ID
        
        Args:
            session: Сессия БД
            digest_id: ID дайджеста
            
        Returns:
            Словарь с данными дайджеста или None
        """
        try:
            digest = session.query(Digest).filter(Digest.digest_id == digest_id).first()
            if not digest:
                return None
            
            items = []
            for digest_item in digest.items:
                content = digest_item.content
                source = session.query(ContentSource).filter(
                    ContentSource.source_id == content.source_id
                ).first()
                
                items.append({
                    'content_id': content.content_id,
                    'annotation': digest_item.annotation,
                    'rank': digest_item.rank,
                    'source_name': source.url if source else 'Unknown',
                    'original_url': content.original_url,
                    'published_at': content.published_at.isoformat() if content.published_at else None
                })
            
            return {
                'digest_id': digest.digest_id,
                'user_id': digest.user_id,
                'period_start': digest.period_start.isoformat(),
                'period_end': digest.period_end.isoformat(),
                'created_at': digest.created_at.isoformat(),
                'items': items
            }
            
        except Exception as e:
            logger.error(f"Error getting digest: {e}")
            return None
    
    def get_content_with_source(
        self,
        session: Session,
        content_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Получить контент с информацией об источнике
        
        Args:
            session: Сессия БД
            content_ids: Список ID контента
            
        Returns:
            Список словарей с данными контента и источника
        """
        try:
            results = session.query(ContentUnit, ContentSource).join(
                ContentSource, ContentUnit.source_id == ContentSource.source_id
            ).filter(ContentUnit.content_id.in_(content_ids)).all()
            
            content_list = []
            for content, source in results:
                content_list.append({
                    'content_id': content.content_id,
                    'summary': content.summary,
                    'text': content.text,
                    'author': content.author,
                    'published_at': content.published_at.isoformat() if content.published_at else None,
                    'original_url': content.original_url,
                    'source_name': source.url,
                    'platform': source.platform_type,
                    'topic_tags': content.topic_tags or []
                })
            
            return content_list
            
        except Exception as e:
            logger.error(f"Error getting content with source: {e}")
            return []


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()
