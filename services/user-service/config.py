"""
Configuration management for User Service
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class for User Service"""
    
    # Database configuration
    database_url: str
    sql_echo: bool
    
    # gRPC configuration
    grpc_port: int
    grpc_max_workers: int
    
    # Logging configuration
    log_level: str
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Load configuration from environment variables
        
        Returns:
            Config instance
        """
        return cls(
            database_url=os.getenv(
                'DATABASE_URL',
                'postgresql://user:password@postgres:5432/content_filter_db'
            ),
            sql_echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
            grpc_port=int(os.getenv('GRPC_PORT', '50051')),
            grpc_max_workers=int(os.getenv('GRPC_MAX_WORKERS', '10')),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )
    
    def validate(self) -> bool:
        """
        Validate configuration
        
        Returns:
            True if valid, raises ValueError otherwise
        """
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        
        if self.grpc_port < 1 or self.grpc_port > 65535:
            raise ValueError("GRPC_PORT must be between 1 and 65535")
        
        if self.grpc_max_workers < 1:
            raise ValueError("GRPC_MAX_WORKERS must be at least 1")
        
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_log_levels}")
        
        return True


# Global config instance
config = Config.from_env()
