"""gRPC client for Feedback Service"""
import logging
import sys
import grpc

# Add shared proto path
sys.path.insert(0, '../../shared')

from shared.proto import feedback_service_pb2
from shared.proto import feedback_service_pb2_grpc

logger = logging.getLogger(__name__)


class FeedbackServiceClient:
    """Client for Feedback Service gRPC API"""
    
    def __init__(self, host: str = "feedback-service", port: int = 50055):
        self.host = host
        self.port = port
        self.channel = None
        self.stub = None
    
    async def connect(self):
        """Connect to Feedback Service"""
        try:
            self.channel = grpc.aio.insecure_channel(f'{self.host}:{self.port}')
            self.stub = feedback_service_pb2_grpc.FeedbackServiceStub(self.channel)
            logger.info(f"Connected to Feedback Service at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Feedback Service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("Disconnected from Feedback Service")
    
    async def save_feedback(self, user_id: int, content_id: int, reaction: str) -> dict:
        """
        Save user feedback
        
        Args:
            user_id: User ID
            content_id: Content ID
            reaction: Reaction type (relevant, not_relevant, saved, hidden)
        
        Returns:
            Dictionary with feedback_id and success status
        """
        try:
            request = feedback_service_pb2.SaveFeedbackRequest(
                user_id=user_id,
                content_id=content_id,
                reaction=reaction
            )
            
            response = await self.stub.SaveFeedback(request)
            
            return {
                'feedback_id': response.feedback_id,
                'success': response.success,
                'message': response.message
            }
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error in save_feedback: {e.code()} - {e.details()}")
            return {'feedback_id': 0, 'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error in save_feedback: {e}")
            return {'feedback_id': 0, 'success': False, 'message': str(e)}
    
    async def get_user_feedback(self, user_id: int, limit: int = 100, reaction_filter: str = None) -> dict:
        """
        Get feedback for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            reaction_filter: Optional filter by reaction type
        
        Returns:
            Dictionary with feedback items
        """
        try:
            request = feedback_service_pb2.GetUserFeedbackRequest(
                user_id=user_id,
                limit=limit
            )
            
            if reaction_filter:
                request.reaction_filter = reaction_filter
            
            response = await self.stub.GetUserFeedback(request)
            
            items = [
                {
                    'feedback_id': item.feedback_id,
                    'content_id': item.content_id,
                    'reaction': item.reaction,
                    'created_at': item.created_at
                }
                for item in response.items
            ]
            
            return {
                'items': items,
                'success': response.success,
                'message': response.message
            }
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error in get_user_feedback: {e.code()} - {e.details()}")
            return {'items': [], 'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error in get_user_feedback: {e}")
            return {'items': [], 'success': False, 'message': str(e)}
    
    async def save_quality_rating(self, user_id: int, rating: int, digest_id: int = None, comment: str = None) -> dict:
        """
        Save quality rating
        
        Args:
            user_id: User ID
            rating: Rating value (1-10)
            digest_id: Optional digest ID
            comment: Optional comment
        
        Returns:
            Dictionary with rating_id and success status
        """
        try:
            request = feedback_service_pb2.SaveQualityRatingRequest(
                user_id=user_id,
                rating=rating
            )
            
            if digest_id is not None:
                request.digest_id = digest_id
            
            if comment:
                request.comment = comment
            
            response = await self.stub.SaveQualityRating(request)
            
            return {
                'rating_id': response.rating_id,
                'success': response.success,
                'message': response.message
            }
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error in save_quality_rating: {e.code()} - {e.details()}")
            return {'rating_id': 0, 'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Error in save_quality_rating: {e}")
            return {'rating_id': 0, 'success': False, 'message': str(e)}
    
    async def get_quality_statistics(self, user_id: int, weeks: int = 8) -> dict:
        """
        Get quality statistics for a user
        
        Args:
            user_id: User ID
            weeks: Number of weeks to include
        
        Returns:
            Dictionary with statistics
        """
        try:
            request = feedback_service_pb2.GetQualityStatisticsRequest(
                user_id=user_id,
                weeks=weeks
            )
            
            response = await self.stub.GetQualityStatistics(request)
            
            weekly_stats = [
                {
                    'week_number': ws.week_number,
                    'average_rating': ws.average_rating,
                    'count': ws.count
                }
                for ws in response.weekly_stats
            ]
            
            return {
                'total_ratings': response.total_ratings,
                'average_rating': response.average_rating,
                'weekly_stats': weekly_stats,
                'success': response.success,
                'message': response.message
            }
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error in get_quality_statistics: {e.code()} - {e.details()}")
            return {
                'total_ratings': 0,
                'average_rating': 0.0,
                'weekly_stats': [],
                'success': False,
                'message': str(e)
            }
        except Exception as e:
            logger.error(f"Error in get_quality_statistics: {e}")
            return {
                'total_ratings': 0,
                'average_rating': 0.0,
                'weekly_stats': [],
                'success': False,
                'message': str(e)
            }
    
    async def get_feedback_statistics(self, user_id: int) -> dict:
        """
        Get feedback statistics for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary with feedback counts by reaction type
        """
        try:
            # Get all feedback for the user
            result = await self.get_user_feedback(user_id, limit=1000)
            
            if not result['success']:
                return {}
            
            # Count by reaction type
            stats = {
                'relevant': 0,
                'not_relevant': 0,
                'saved': 0,
                'hidden': 0
            }
            
            for item in result['items']:
                reaction = item['reaction']
                if reaction in stats:
                    stats[reaction] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in get_feedback_statistics: {e}")
            return {}


# Global client instance
feedback_service_client = FeedbackServiceClient()
