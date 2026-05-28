"""
Main entry point for User Service
"""
import logging
import sys
import os

from config import config
from database import db_manager
from grpc_server import serve


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main function"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Validate configuration
        config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize database
        logger.info("Initializing database...")
        db_manager.create_tables()
        logger.info("Database initialized successfully")
        
        # Start gRPC server
        logger.info(f"Starting User Service on port {config.grpc_port}...")
        serve(port=config.grpc_port)
        
    except Exception as e:
        logger.error(f"Failed to start User Service: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
