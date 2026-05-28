"""Configuration for Feedback Service"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Feedback service settings"""
    
    # Service settings
    service_name: str = "feedback-service"
    grpc_port: int = 50055
    log_level: str = "INFO"
    
    # Database settings
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "content_filter_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    
    # Ranking service settings (for triggering profile updates)
    ranking_service_host: str = "ranking-service"
    ranking_service_port: int = 50053
    
    @property
    def database_url(self) -> str:
        """Get database URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
