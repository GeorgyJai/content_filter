"""gRPC server for Feedback Service"""
import logging
import sys
from concurrent import futures
import grpc

# Add shared proto path to sys.path
sys.path.insert(0, '/app/shared/proto')

from feedback_service_pb2 import *
import feedback_service_pb2_grpc
from database import db_manager

logger = logging.getLogger(__name__)


class FeedbackServiceServicer(feedback_service_pb2_grpc.FeedbackServiceServicer):
    """Implementation of FeedbackService gRPC service"""
    
    def SaveFeedback(self, request, context):
        """Save user feedback"""
        try:
            logger.info(f"SaveFeedback called: user={request.user_id}, content={request.content_id}, reaction={request.reaction}")
            
            feedback_id = db_manager.save_feedback(
                user_id=request.user_id,
                content_id=request.content_id,
                reaction=request.reaction
            )
            
            if feedback_id:
                return feedback_service_pb2.FeedbackResponse(
                    feedback_id=feedback_id,
                    success=True,
                    message="Feedback saved successfully"
                )
            else:
                return feedback_service_pb2.FeedbackResponse(
                    feedback_id=0,
                    success=False,
                    message="Failed to save feedback"
                )
                
        except Exception as e:
            logger.error(f"Error in SaveFeedback: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.FeedbackResponse(
                feedback_id=0,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def SaveBatchFeedback(self, request, context):
        """Save multiple feedbacks at once"""
        try:
            logger.info(f"SaveBatchFeedback called: {len(request.feedbacks)} items")
            
            feedbacks = [
                {
                    'user_id': fb.user_id,
                    'content_id': fb.content_id,
                    'reaction': fb.reaction
                }
                for fb in request.feedbacks
            ]
            
            saved_count = db_manager.save_batch_feedback(feedbacks)
            
            return feedback_service_pb2.BatchFeedbackResponse(
                saved_count=saved_count,
                success=True,
                message=f"Saved {saved_count} feedbacks"
            )
            
        except Exception as e:
            logger.error(f"Error in SaveBatchFeedback: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.BatchFeedbackResponse(
                saved_count=0,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def GetUserFeedback(self, request, context):
        """Get feedback for a user"""
        try:
            logger.info(f"GetUserFeedback called: user={request.user_id}")
            
            limit = request.limit if request.HasField('limit') else 100
            reaction_filter = request.reaction_filter if request.HasField('reaction_filter') else None
            
            feedbacks = db_manager.get_user_feedback(
                user_id=request.user_id,
                limit=limit,
                reaction_filter=reaction_filter
            )
            
            items = [
                feedback_service_pb2.FeedbackItem(
                    feedback_id=fb['feedback_id'],
                    content_id=fb['content_id'],
                    reaction=fb['reaction'],
                    created_at=fb['created_at']
                )
                for fb in feedbacks
            ]
            
            return feedback_service_pb2.UserFeedbackResponse(
                items=items,
                success=True,
                message=f"Found {len(items)} feedback items"
            )
            
        except Exception as e:
            logger.error(f"Error in GetUserFeedback: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.UserFeedbackResponse(
                items=[],
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def GetContentFeedback(self, request, context):
        """Get feedback statistics for content"""
        try:
            logger.info(f"GetContentFeedback called: content={request.content_id}")
            
            stats = db_manager.get_content_feedback(content_id=request.content_id)
            
            return feedback_service_pb2.ContentFeedbackResponse(
                content_id=stats['content_id'],
                relevant_count=stats['relevant_count'],
                not_relevant_count=stats['not_relevant_count'],
                saved_count=stats['saved_count'],
                hidden_count=stats['hidden_count'],
                success=True,
                message="Statistics retrieved"
            )
            
        except Exception as e:
            logger.error(f"Error in GetContentFeedback: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.ContentFeedbackResponse(
                content_id=request.content_id,
                relevant_count=0,
                not_relevant_count=0,
                saved_count=0,
                hidden_count=0,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def SaveQualityRating(self, request, context):
        """Save quality rating"""
        try:
            logger.info(f"SaveQualityRating called: user={request.user_id}, rating={request.rating}")
            
            digest_id = request.digest_id if request.HasField('digest_id') else None
            comment = request.comment if request.HasField('comment') else None
            
            rating_id = db_manager.save_quality_rating(
                user_id=request.user_id,
                rating=request.rating,
                digest_id=digest_id,
                comment=comment
            )
            
            if rating_id:
                return feedback_service_pb2.QualityRatingResponse(
                    rating_id=rating_id,
                    success=True,
                    message="Quality rating saved successfully"
                )
            else:
                return feedback_service_pb2.QualityRatingResponse(
                    rating_id=0,
                    success=False,
                    message="Failed to save quality rating"
                )
                
        except Exception as e:
            logger.error(f"Error in SaveQualityRating: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.QualityRatingResponse(
                rating_id=0,
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def GetUserQualityRatings(self, request, context):
        """Get quality ratings for a user"""
        try:
            logger.info(f"GetUserQualityRatings called: user={request.user_id}")
            
            limit = request.limit if request.HasField('limit') else 100
            
            ratings = db_manager.get_user_quality_ratings(
                user_id=request.user_id,
                limit=limit
            )
            
            items = [
                feedback_service_pb2.QualityRatingItem(
                    rating_id=r['rating_id'],
                    digest_id=r['digest_id'] if r['digest_id'] else 0,
                    rating=r['rating'],
                    comment=r['comment'] if r['comment'] else "",
                    created_at=r['created_at']
                )
                for r in ratings
            ]
            
            return feedback_service_pb2.QualityRatingsResponse(
                items=items,
                success=True,
                message=f"Found {len(items)} quality ratings"
            )
            
        except Exception as e:
            logger.error(f"Error in GetUserQualityRatings: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.QualityRatingsResponse(
                items=[],
                success=False,
                message=f"Error: {str(e)}"
            )
    
    def GetQualityStatistics(self, request, context):
        """Get quality statistics for a user"""
        try:
            logger.info(f"GetQualityStatistics called: user={request.user_id}")
            
            weeks = request.weeks if request.HasField('weeks') else 8
            
            stats = db_manager.get_quality_statistics(
                user_id=request.user_id,
                weeks=weeks
            )
            
            weekly_stats = [
                feedback_service_pb2.WeeklyStats(
                    week_number=ws['week_number'],
                    average_rating=ws['average_rating'],
                    count=ws['count']
                )
                for ws in stats.get('weekly_stats', [])
            ]
            
            return feedback_service_pb2.QualityStatisticsResponse(
                total_ratings=stats.get('total_ratings', 0),
                average_rating=stats.get('average_rating', 0.0),
                weekly_stats=weekly_stats,
                success=True,
                message="Statistics retrieved"
            )
            
        except Exception as e:
            logger.error(f"Error in GetQualityStatistics: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return feedback_service_pb2.QualityStatisticsResponse(
                total_ratings=0,
                average_rating=0.0,
                weekly_stats=[],
                success=False,
                message=f"Error: {str(e)}"
            )


def serve(port: int = 50055):
    """Start gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    feedback_service_pb2_grpc.add_FeedbackServiceServicer_to_server(
        FeedbackServiceServicer(), server
    )
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"Feedback Service gRPC server started on port {port}")
    return server
