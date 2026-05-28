"""
Database models for User Service
"""
from sqlalchemy import Column, Integer, BigInteger, String, TIMESTAMP, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model representing system users"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    platform = Column(String(50), nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'platform': self.platform,
            'telegram_id': self.telegram_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserProfile(Base):
    """User profile model for storing user preferences"""
    __tablename__ = 'user_profiles'
    
    profile_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, unique=True)
    preferences = Column(JSON, default=dict)
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self):
        return {
            'profile_id': self.profile_id,
            'user_id': self.user_id,
            'preferences': self.preferences,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ContentSource(Base):
    """Content source model representing channels/sources"""
    __tablename__ = 'content_sources'
    
    source_id = Column(Integer, primary_key=True, autoincrement=True)
    platform_type = Column(String(50), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    topic = Column(String(255))
    publish_frequency = Column(String(50))
    
    def to_dict(self):
        return {
            'source_id': self.source_id,
            'platform_type': self.platform_type,
            'url': self.url,
            'topic': self.topic,
            'publish_frequency': self.publish_frequency
        }


class Subscription(Base):
    """Subscription model for user-source relationships"""
    __tablename__ = 'subscriptions'
    
    subscription_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    source_id = Column(Integer, ForeignKey('content_sources.source_id'), nullable=False)
    subscribed_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'source_id', name='uq_user_source'),
    )
    
    def to_dict(self):
        return {
            'subscription_id': self.subscription_id,
            'user_id': self.user_id,
            'source_id': self.source_id,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None
        }
