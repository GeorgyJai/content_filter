"""
gRPC server implementation for User Service
"""
import grpc
from concurrent import futures
import logging
import sys
import os

# Add shared proto path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'proto'))

import user_service_pb2
import user_service_pb2_grpc

from database import db_manager
from service import UserService

logger = logging.getLogger(__name__)


class UserServiceServicer(user_service_pb2_grpc.UserServiceServicer):
    """gRPC servicer implementation"""
    
    def CreateUser(self, request, context):
        """Create a new user"""
        try:
            with db_manager.get_session() as session:
                service = UserService(session)
                
                # Check if user already exists
                existing_user = service.get_user_by_username(
                    request.username,
                    request.platform
                )
                
                if existing_user:
                    return user_service_pb2.UserResponse(
                        user_id=existing_user.user_id,
                        username=existing_user.username,
                        platform=existing_user.platform
                    )
                
                # Create new user
                user = service.create_user(request.username, request.platform)
                
                return user_service_pb2.UserResponse(
                    user_id=user.user_id,
                    username=user.username,
                    platform=user.platform
                )
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.UserResponse()
    
    def GetUserProfile(self, request, context):
        """Get user profile"""
        try:
            with db_manager.get_session() as session:
                service = UserService(session)
                profile = service.get_user_profile(request.user_id)
                
                if not profile:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Profile not found for user {request.user_id}")
                    return user_service_pb2.UserProfileResponse()
                
                import json
                return user_service_pb2.UserProfileResponse(
                    profile_id=profile.profile_id,
                    user_id=profile.user_id,
                    preferences_json=json.dumps(profile.preferences or {}),
                    updated_at=profile.updated_at.isoformat() if profile.updated_at else ""
                )
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.UserProfileResponse()
    
    def UpdateUserPreferences(self, request, context):
        """Update user preferences"""
        try:
            with db_manager.get_session() as session:
                service = UserService(session)
                
                import json
                preferences = json.loads(request.preferences_json)
                profile = service.update_user_preferences(request.user_id, preferences)
                
                return user_service_pb2.UserProfileResponse(
                    profile_id=profile.profile_id,
                    user_id=profile.user_id,
                    preferences_json=json.dumps(profile.preferences or {}),
                    updated_at=profile.updated_at.isoformat() if profile.updated_at else ""
                )
        except ValueError as e:
            logger.error(f"Error updating preferences: {e}")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return user_service_pb2.UserProfileResponse()
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.UserProfileResponse()
    
    def AddSubscription(self, request, context):
        """Add subscription for user"""
        try:
            with db_manager.get_session() as session:
                service = UserService(session)
                subscription = service.add_subscription(
                    request.user_id,
                    request.source_url,
                    request.platform_type
                )
                
                return user_service_pb2.SubscriptionResponse(
                    subscription_id=subscription.subscription_id,
                    success=True,
                    message="Subscription added successfully"
                )
        except ValueError as e:
            logger.error(f"Error adding subscription: {e}")
            return user_service_pb2.SubscriptionResponse(
                subscription_id=0,
                success=False,
                message=str(e)
            )
        except Exception as e:
            logger.error(f"Error adding subscription: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.SubscriptionResponse(
                subscription_id=0,
                success=False,
                message=str(e)
            )
    
    def RemoveSubscription(self, request, context):
        """Remove subscription"""
        try:
            with db_manager.get_session() as session:
                service = UserService(session)
                success = service.remove_subscription(
                    request.user_id,
                    request.source_id
                )
                
                return user_service_pb2.SubscriptionResponse(
                    subscription_id=request.source_id,
                    success=success,
                    message="Subscription removed" if success else "Subscription not found"
                )
        except Exception as e:
            logger.error(f"Error removing subscription: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.SubscriptionResponse(
                subscription_id=0,
                success=False,
                message=str(e)
            )
    
    def GetUserSubscriptions(self, request, context):
        """Get all user subscriptions"""
        try:
            with db_manager.get_session() as session:
                service = UserService(session)
                subscriptions = service.get_user_subscriptions(request.user_id)
                
                subscription_list = []
                for sub in subscriptions:
                    subscription_list.append(
                        user_service_pb2.Subscription(
                            subscription_id=sub['subscription_id'],
                            source_id=sub['source_id'],
                            source_url=sub['source_url'],
                            platform_type=sub['platform_type']
                        )
                    )
                
                return user_service_pb2.SubscriptionsListResponse(
                    subscriptions=subscription_list
                )
        except Exception as e:
            logger.error(f"Error getting subscriptions: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return user_service_pb2.SubscriptionsListResponse()


def serve(port: int = 50051):
    """Start gRPC server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_service_pb2_grpc.add_UserServiceServicer_to_server(
        UserServiceServicer(),
        server
    )
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    logger.info(f"User Service gRPC server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)
