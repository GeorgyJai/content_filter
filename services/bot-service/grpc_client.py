"""gRPC client for User Service"""
import grpc
import logging
from typing import Optional, Dict, Any, List
import sys
import os

# Add shared proto path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'proto'))

try:
    import user_service_pb2
    import user_service_pb2_grpc
except ImportError:
    logging.warning("Proto files not generated yet. Run: python -m grpc_tools.protoc")
    user_service_pb2 = None
    user_service_pb2_grpc = None

from config import settings

logger = logging.getLogger(__name__)


class UserServiceClient:
    """Client for User Service gRPC API"""
    
    def __init__(self, address: Optional[str] = None):
        """Initialize gRPC client
        
        Args:
            address: gRPC server address (host:port)
        """
        self.address = address or settings.user_service_address
        self.channel = None
        self.stub = None
        
    async def connect(self):
        """Establish connection to User Service"""
        try:
            self.channel = grpc.aio.insecure_channel(self.address)
            if user_service_pb2_grpc:
                self.stub = user_service_pb2_grpc.UserServiceStub(self.channel)
            logger.info(f"Connected to User Service at {self.address}")
        except Exception as e:
            logger.error(f"Failed to connect to User Service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("Disconnected from User Service")
    
    async def create_user(self, username: str, platform: str = "telegram") -> Optional[Dict[str, Any]]:
        """Create new user
        
        Args:
            username: Username
            platform: Platform name (default: telegram)
            
        Returns:
            User data dict or None if failed
        """
        if not self.stub or not user_service_pb2:
            logger.error("gRPC stub not initialized")
            return None
            
        try:
            request = user_service_pb2.CreateUserRequest(
                username=username,
                platform=platform
            )
            response = await self.stub.CreateUser(request)
            
            return {
                "user_id": response.user_id,
                "username": response.username,
                "platform": response.platform
            }
        except grpc.RpcError as e:
            logger.error(f"Failed to create user: {e.code()} - {e.details()}")
            return None
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile
        
        Args:
            user_id: User ID
            
        Returns:
            Profile data dict or None if failed
        """
        if not self.stub or not user_service_pb2:
            logger.error("gRPC stub not initialized")
            return None
            
        try:
            request = user_service_pb2.GetUserProfileRequest(user_id=user_id)
            response = await self.stub.GetUserProfile(request)
            
            return {
                "profile_id": response.profile_id,
                "user_id": response.user_id,
                "preferences_json": response.preferences_json,
                "updated_at": response.updated_at
            }
        except grpc.RpcError as e:
            logger.error(f"Failed to get user profile: {e.code()} - {e.details()}")
            return None
    
    async def update_preferences(self, user_id: int, preferences_json: str) -> Optional[Dict[str, Any]]:
        """Update user preferences
        
        Args:
            user_id: User ID
            preferences_json: JSON string with preferences
            
        Returns:
            Updated profile data or None if failed
        """
        if not self.stub or not user_service_pb2:
            logger.error("gRPC stub not initialized")
            return None
            
        try:
            request = user_service_pb2.UpdatePreferencesRequest(
                user_id=user_id,
                preferences_json=preferences_json
            )
            response = await self.stub.UpdateUserPreferences(request)
            
            return {
                "profile_id": response.profile_id,
                "user_id": response.user_id,
                "preferences_json": response.preferences_json,
                "updated_at": response.updated_at
            }
        except grpc.RpcError as e:
            logger.error(f"Failed to update preferences: {e.code()} - {e.details()}")
            return None
    
    async def add_subscription(self, user_id: int, source_url: str, platform_type: str) -> Optional[Dict[str, Any]]:
        """Add subscription to content source
        
        Args:
            user_id: User ID
            source_url: URL of content source
            platform_type: Platform type (telegram, vk, youtube)
            
        Returns:
            Subscription data or None if failed
        """
        if not self.stub or not user_service_pb2:
            logger.error("gRPC stub not initialized")
            return None
            
        try:
            request = user_service_pb2.AddSubscriptionRequest(
                user_id=user_id,
                source_url=source_url,
                platform_type=platform_type
            )
            response = await self.stub.AddSubscription(request)
            
            return {
                "subscription_id": response.subscription_id,
                "success": response.success,
                "message": response.message
            }
        except grpc.RpcError as e:
            logger.error(f"Failed to add subscription: {e.code()} - {e.details()}")
            return None
    
    async def remove_subscription(self, user_id: int, source_id: int) -> Optional[Dict[str, Any]]:
        """Remove subscription
        
        Args:
            user_id: User ID
            source_id: Source ID to unsubscribe from
            
        Returns:
            Result data or None if failed
        """
        if not self.stub or not user_service_pb2:
            logger.error("gRPC stub not initialized")
            return None
            
        try:
            request = user_service_pb2.RemoveSubscriptionRequest(
                user_id=user_id,
                source_id=source_id
            )
            response = await self.stub.RemoveSubscription(request)
            
            return {
                "subscription_id": response.subscription_id,
                "success": response.success,
                "message": response.message
            }
        except grpc.RpcError as e:
            logger.error(f"Failed to remove subscription: {e.code()} - {e.details()}")
            return None
    
    async def get_subscriptions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user subscriptions
        
        Args:
            user_id: User ID
            
        Returns:
            List of subscriptions
        """
        if not self.stub or not user_service_pb2:
            logger.error("gRPC stub not initialized")
            return []
            
        try:
            request = user_service_pb2.GetSubscriptionsRequest(user_id=user_id)
            response = await self.stub.GetUserSubscriptions(request)
            
            subscriptions = []
            for sub in response.subscriptions:
                subscriptions.append({
                    "subscription_id": sub.subscription_id,
                    "source_id": sub.source_id,
                    "source_url": sub.source_url,
                    "platform_type": sub.platform_type
                })
            
            return subscriptions
        except grpc.RpcError as e:
            logger.error(f"Failed to get subscriptions: {e.code()} - {e.details()}")
            return []


# Global client instance
user_service_client = UserServiceClient()
