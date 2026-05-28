"""Database operations for tracking processed videos."""
import psycopg2
from psycopg2.extras import RealDictCursor
import structlog
from typing import Optional, Set
from config import config

logger = structlog.get_logger()


class VideoTracker:
    """Track processed YouTube videos to avoid duplicates."""
    
    def __init__(self):
        """Initialize video tracker."""
        self.connection: Optional[psycopg2.extensions.connection] = None
        self._connect()
        self._create_table()
    
    def _connect(self) -> None:
        """Establish connection to PostgreSQL."""
        try:
            self.connection = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                database=config.POSTGRES_DB,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD
            )
            logger.info("postgres_connected", host=config.POSTGRES_HOST)
        except Exception as e:
            logger.error("postgres_connection_failed", error=str(e))
            raise
    
    def _create_table(self) -> None:
        """Create table for tracking processed videos if it doesn't exist."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS youtube_processed_videos (
                        video_id VARCHAR(50) PRIMARY KEY,
                        channel_id VARCHAR(50) NOT NULL,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        title TEXT,
                        published_at TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_youtube_channel_id 
                    ON youtube_processed_videos(channel_id);
                    
                    CREATE INDEX IF NOT EXISTS idx_youtube_processed_at 
                    ON youtube_processed_videos(processed_at);
                """)
                self.connection.commit()
                logger.info("video_tracker_table_ready")
        except Exception as e:
            logger.error("create_table_failed", error=str(e))
            self.connection.rollback()
    
    def is_processed(self, video_id: str) -> bool:
        """
        Check if video has been processed.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            True if video was already processed, False otherwise
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM youtube_processed_videos WHERE video_id = %s",
                    (video_id,)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error("is_processed_check_failed", error=str(e), video_id=video_id)
            return False
    
    def mark_processed(self, video_id: str, channel_id: str, title: str, published_at: str) -> bool:
        """
        Mark video as processed.
        
        Args:
            video_id: YouTube video ID
            channel_id: YouTube channel ID
            title: Video title
            published_at: Publication timestamp
            
        Returns:
            True if marked successfully, False otherwise
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO youtube_processed_videos 
                    (video_id, channel_id, title, published_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (video_id) DO NOTHING
                    """,
                    (video_id, channel_id, title, published_at)
                )
                self.connection.commit()
                return True
        except Exception as e:
            logger.error("mark_processed_failed", error=str(e), video_id=video_id)
            self.connection.rollback()
            return False
    
    def get_processed_videos(self, channel_id: str, limit: int = 100) -> Set[str]:
        """
        Get set of processed video IDs for a channel.
        
        Args:
            channel_id: YouTube channel ID
            limit: Maximum number of videos to retrieve
            
        Returns:
            Set of video IDs
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT video_id FROM youtube_processed_videos 
                    WHERE channel_id = %s 
                    ORDER BY processed_at DESC 
                    LIMIT %s
                    """,
                    (channel_id, limit)
                )
                return {row[0] for row in cursor.fetchall()}
        except Exception as e:
            logger.error("get_processed_videos_failed", error=str(e), channel_id=channel_id)
            return set()
    
    def close(self) -> None:
        """Close database connection."""
        try:
            if self.connection:
                self.connection.close()
                logger.info("postgres_connection_closed")
        except Exception as e:
            logger.error("close_connection_failed", error=str(e))
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
