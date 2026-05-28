"""Configuration for Bot Service"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Bot service settings"""
    
    # Telegram Bot
    bot_token: str = Field(..., alias="BOT_TOKEN")
    
    # Telegram API (for folder parsing with Telethon)
    telegram_api_id: int = Field(default=0, alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", alias="TELEGRAM_API_HASH")
    
    # User Service gRPC
    user_service_host: str = Field(default="user-service", alias="USER_SERVICE_HOST")
    user_service_port: int = Field(default=50051, alias="USER_SERVICE_PORT")
    
    # Digest Service gRPC
    digest_service_host: str = Field(default="digest-service", alias="DIGEST_SERVICE_HOST")
    digest_service_port: int = Field(default=50052, alias="DIGEST_SERVICE_PORT")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"
    
    @property
    def user_service_address(self) -> str:
        """Get full user service gRPC address"""
        return f"{self.user_service_host}:{self.user_service_port}"
    
    @property
    def digest_service_address(self) -> str:
        """Get full digest service gRPC address"""
        return f"{self.digest_service_host}:{self.digest_service_port}"


# Global settings instance
settings = Settings()
