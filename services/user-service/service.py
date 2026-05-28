"""
User Service business logic
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict
import json
import logging

from models import User, UserProfile, ContentSource, Subscription

logger = logging.getLogger(__name__)


class UserService:
    """Business logic for user operations"""
    
    def __init__(self, db_session: Session):
        """
        Initialize user service
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def create_user(self, username: str, platform: str) -> User:
        """
        Create a new user
        
        Args:
            username: User's username
            platform: Platform identifier (telegram, etc.)
            
        Returns:
            Created User object
            
        Raises:
            ValueError: If user creation fails
        """
        try:
            user = User(username=username, platform=platform)
            self.db.add(user)
            self.db.flush()
            
            # Create default profile
            profile = UserProfile(
                user_id=user.user_id,
                preferences={}
            )
            self.db.add(profile)
            self.db.flush()
            
            logger.info(f"Created user {user.user_id} with username {username}")
            return user
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise ValueError(f"User creation failed: {e}")
    
    def get_user(self, user_id: int) -> Optional[User]:
        """
        Get user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def get_user_by_username(self, username: str, platform: str) -> Optional[User]:
        """
        Get user by username and platform
        
        Args:
            username: User's username
            platform: Platform identifier
            
        Returns:
            User object or None if not found
        """
        return self.db.query(User).filter(
            User.username == username,
            User.platform == platform
        ).first()
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """
        Get user profile
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfile object or None if not found
        """
        return self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
    
    def update_user_preferences(self, user_id: int, preferences: Dict) -> UserProfile:
        """
        Update user preferences
        
        Args:
            user_id: User ID
            preferences: Dictionary of preferences
            
        Returns:
            Updated UserProfile object
            
        Raises:
            ValueError: If profile not found
        """
        profile = self.get_user_profile(user_id)
        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")
        
        # Merge with existing preferences
        current_prefs = profile.preferences or {}
        current_prefs.update(preferences)
        profile.preferences = current_prefs
        
        self.db.flush()
        logger.info(f"Updated preferences for user {user_id}")
        return profile
    
    def get_or_create_source(self, platform_type: str, url: str, 
                            topic: str = None, publish_frequency: str = None) -> ContentSource:
        """
        Get existing source or create new one
        
        Args:
            platform_type: Platform type (telegram, vk, youtube)
            url: Source URL
            topic: Optional topic
            publish_frequency: Optional publish frequency
            
        Returns:
            ContentSource object
        """
        source = self.db.query(ContentSource).filter(
            ContentSource.url == url
        ).first()
        
        if source:
            return source
        
        source = ContentSource(
            platform_type=platform_type,
            url=url,
            topic=topic,
            publish_frequency=publish_frequency
        )
        self.db.add(source)
        self.db.flush()
        logger.info(f"Created new source {source.source_id} for {url}")
        return source
    
    def add_subscription(self, user_id: int, source_url: str, 
                        platform_type: str) -> Subscription:
        """
        Add subscription for user
        
        Args:
            user_id: User ID
            source_url: Source URL
            platform_type: Platform type
            
        Returns:
            Created Subscription object
            
        Raises:
            ValueError: If subscription already exists or user not found
        """
        # Verify user exists
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get or create source
        source = self.get_or_create_source(platform_type, source_url)
        
        # Check if subscription already exists
        existing = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.source_id == source.source_id
        ).first()
        
        if existing:
            logger.info(f"Subscription already exists for user {user_id} and source {source.source_id}")
            return existing
        
        # Create subscription
        subscription = Subscription(
            user_id=user_id,
            source_id=source.source_id
        )
        self.db.add(subscription)
        self.db.flush()
        logger.info(f"Created subscription {subscription.subscription_id} for user {user_id}")
        return subscription
    
    def remove_subscription(self, user_id: int, source_id: int) -> bool:
        """
        Remove subscription
        
        Args:
            user_id: User ID
            source_id: Source ID
            
        Returns:
            True if removed, False if not found
        """
        subscription = self.db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.source_id == source_id
        ).first()
        
        if not subscription:
            return False
        
        self.db.delete(subscription)
        self.db.flush()
        logger.info(f"Removed subscription for user {user_id} and source {source_id}")
        return True
    
    def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        """
        Get all subscriptions for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of subscription dictionaries with source details
        """
        subscriptions = self.db.query(Subscription, ContentSource).join(
            ContentSource,
            Subscription.source_id == ContentSource.source_id
        ).filter(
            Subscription.user_id == user_id
        ).all()
        
        result = []
        for sub, source in subscriptions:
            result.append({
                'subscription_id': sub.subscription_id,
                'source_id': source.source_id,
                'source_url': source.url,
                'platform_type': source.platform_type,
                'topic': source.topic,
                'subscribed_at': sub.subscribed_at.isoformat() if sub.subscribed_at else None
            })
        
        return result
