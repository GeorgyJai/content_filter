"""Database operations for Feedback Service"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey, Text, Boolean, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func, and_, or_

from config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# ============================================
# Database Models
# ============================================

class Feedback(Base):
    """Feedback model"""
    __tablename__ = 'feedback'
    
    feedback_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    content_id = Column(Integer, ForeignKey('content_units.content_id'), nullable=False)
    reaction = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class QualityRating(Base):
    """Quality rating model"""
    __tablename__ = 'quality_ratings'
    
    rating_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    digest_id = Column(Integer, ForeignKey('digests.digest_id'), nullable=True)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 10', name='check_rating_range'),
    )


# ============================================
# Database Manager
# ============================================

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.engine = create_engine(
            settings.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        logger.info(f"Database connection initialized: {settings.postgres_host}")
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    # ============================================
    # Feedback Operations
    # ============================================
    
    def save_feedback(self, user_id: int, content_id: int, reaction: str) -> Optional[int]:
        """
        Save user feedback
        
        Args:
            user_id: User ID
            content_id: Content ID
            reaction: Reaction type (relevant, not_relevant, saved, hidden)
        
        Returns:
            Feedback ID if successful, None otherwise
        """
        session = self.get_session()
        try:
            # Check if feedback already exists
            existing = session.query(Feedback).filter(
                and_(
                    Feedback.user_id == user_id,
                    Feedback.content_id == content_id,
                    Feedback.reaction == reaction
                )
            ).first()
            
            if existing:
                logger.info(f"Feedback already exists: user={user_id}, content={content_id}, reaction={reaction}")
                return existing.feedback_id
            
            # Create new feedback
            feedback = Feedback(
                user_id=user_id,
                content_id=content_id,
                reaction=reaction
            )
            
            session.add(feedback)
            session.commit()
            
            logger.info(f"Feedback saved: id={feedback.feedback_id}, user={user_id}, content={content_id}, reaction={reaction}")
            return feedback.feedback_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving feedback: {e}")
            return None
        finally:
            session.close()
    
    def save_batch_feedback(self, feedbacks: List[Dict]) -> int:
        """
        Save multiple feedbacks at once
        
        Args:
            feedbacks: List of feedback dictionaries
        
        Returns:
            Number of feedbacks saved
        """
        session = self.get_session()
        saved_count = 0
        
        try:
            for fb in feedbacks:
                # Check if exists
                existing = session.query(Feedback).filter(
                    and_(
                        Feedback.user_id == fb['user_id'],
                        Feedback.content_id == fb['content_id'],
                        Feedback.reaction == fb['reaction']
                    )
                ).first()
                
                if not existing:
                    feedback = Feedback(**fb)
                    session.add(feedback)
                    saved_count += 1
            
            session.commit()
            logger.info(f"Batch feedback saved: {saved_count} items")
            return saved_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving batch feedback: {e}")
            return saved_count
        finally:
            session.close()
    
    def get_user_feedback(self, user_id: int, limit: int = 100, reaction_filter: Optional[str] = None) -> List[Dict]:
        """
        Get feedback for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            reaction_filter: Filter by reaction type
        
        Returns:
            List of feedback items
        """
        session = self.get_session()
        try:
            query = session.query(Feedback).filter(Feedback.user_id == user_id)
            
            if reaction_filter:
                query = query.filter(Feedback.reaction == reaction_filter)
            
            query = query.order_by(Feedback.created_at.desc()).limit(limit)
            
            feedbacks = query.all()
            
            return [
                {
                    'feedback_id': fb.feedback_id,
                    'content_id': fb.content_id,
                    'reaction': fb.reaction,
                    'created_at': fb.created_at.isoformat() if fb.created_at else None
                }
                for fb in feedbacks
            ]
            
        except Exception as e:
            logger.error(f"Error getting user feedback: {e}")
            return []
        finally:
            session.close()
    
    def get_content_feedback(self, content_id: int) -> Dict:
        """
        Get feedback statistics for a content item
        
        Args:
            content_id: Content ID
        
        Returns:
            Dictionary with feedback counts
        """
        session = self.get_session()
        try:
            feedbacks = session.query(Feedback).filter(Feedback.content_id == content_id).all()
            
            stats = {
                'content_id': content_id,
                'relevant_count': sum(1 for fb in feedbacks if fb.reaction == 'relevant'),
                'not_relevant_count': sum(1 for fb in feedbacks if fb.reaction == 'not_relevant'),
                'saved_count': sum(1 for fb in feedbacks if fb.reaction == 'saved'),
                'hidden_count': sum(1 for fb in feedbacks if fb.reaction == 'hidden')
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting content feedback: {e}")
            return {
                'content_id': content_id,
                'relevant_count': 0,
                'not_relevant_count': 0,
                'saved_count': 0,
                'hidden_count': 0
            }
        finally:
            session.close()
    
    def get_feedback_statistics(self, user_id: int) -> Dict:
        """
        Get feedback statistics for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with feedback statistics
        """
        session = self.get_session()
        try:
            feedbacks = session.query(Feedback).filter(Feedback.user_id == user_id).all()
            
            stats = {
                'relevant': sum(1 for fb in feedbacks if fb.reaction == 'relevant'),
                'not_relevant': sum(1 for fb in feedbacks if fb.reaction == 'not_relevant'),
                'saved': sum(1 for fb in feedbacks if fb.reaction == 'saved'),
                'hidden': sum(1 for fb in feedbacks if fb.reaction == 'hidden')
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting feedback statistics: {e}")
            return {}
        finally:
            session.close()
    
    # ============================================
    # Quality Rating Operations
    # ============================================
    
    def save_quality_rating(self, user_id: int, rating: int, digest_id: Optional[int] = None, comment: Optional[str] = None) -> Optional[int]:
        """
        Save quality rating
        
        Args:
            user_id: User ID
            rating: Rating value (1-10)
            digest_id: Optional digest ID
            comment: Optional comment
        
        Returns:
            Rating ID if successful, None otherwise
        """
        session = self.get_session()
        try:
            quality_rating = QualityRating(
                user_id=user_id,
                digest_id=digest_id,
                rating=rating,
                comment=comment
            )
            
            session.add(quality_rating)
            session.commit()
            
            logger.info(f"Quality rating saved: id={quality_rating.rating_id}, user={user_id}, rating={rating}")
            return quality_rating.rating_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving quality rating: {e}")
            return None
        finally:
            session.close()
    
    def get_user_quality_ratings(self, user_id: int, limit: int = 100) -> List[Dict]:
        """
        Get quality ratings for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of results
        
        Returns:
            List of quality ratings
        """
        session = self.get_session()
        try:
            ratings = session.query(QualityRating).filter(
                QualityRating.user_id == user_id
            ).order_by(QualityRating.created_at.desc()).limit(limit).all()
            
            return [
                {
                    'rating_id': r.rating_id,
                    'digest_id': r.digest_id,
                    'rating': r.rating,
                    'comment': r.comment,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                }
                for r in ratings
            ]
            
        except Exception as e:
            logger.error(f"Error getting quality ratings: {e}")
            return []
        finally:
            session.close()
    
    def get_quality_statistics(self, user_id: int, weeks: int = 8) -> Dict:
        """
        Get quality rating statistics for a user
        
        Args:
            user_id: User ID
            weeks: Number of weeks to include
        
        Returns:
            Dictionary with statistics
        """
        session = self.get_session()
        try:
            # Get all ratings for the user
            ratings = session.query(QualityRating).filter(
                QualityRating.user_id == user_id
            ).order_by(QualityRating.created_at.desc()).all()
            
            if not ratings:
                return {
                    'total_ratings': 0,
                    'average_rating': 0.0,
                    'weekly_stats': []
                }
            
            # Calculate overall statistics
            total_ratings = len(ratings)
            average_rating = sum(r.rating for r in ratings) / total_ratings
            
            # Calculate weekly statistics
            cutoff_date = datetime.utcnow() - timedelta(weeks=weeks)
            recent_ratings = [r for r in ratings if r.created_at >= cutoff_date]
            
            # Group by week
            weekly_stats = {}
            for rating in recent_ratings:
                week_number = rating.created_at.isocalendar()[1]
                year = rating.created_at.year
                key = f"{year}-W{week_number}"
                
                if key not in weekly_stats:
                    weekly_stats[key] = []
                weekly_stats[key].append(rating.rating)
            
            # Calculate averages
            weekly_list = []
            for week_key, week_ratings in sorted(weekly_stats.items()):
                weekly_list.append({
                    'week_number': week_key,
                    'average_rating': sum(week_ratings) / len(week_ratings),
                    'count': len(week_ratings)
                })
            
            return {
                'total_ratings': total_ratings,
                'average_rating': average_rating,
                'weekly_stats': weekly_list
            }
            
        except Exception as e:
            logger.error(f"Error getting quality statistics: {e}")
            return {
                'total_ratings': 0,
                'average_rating': 0.0,
                'weekly_stats': []
            }
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()
