"""Main entry point for Feedback Service"""
import logging
import sys
import signal
import time
from config import settings
from grpc_server import serve

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main function"""
    logger.info(f"Starting {settings.service_name}...")
    logger.info(f"Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    
    # Start gRPC server
    server = serve(port=settings.grpc_port)
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutting down gracefully...")
        server.stop(grace=5)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Keep the server running
    try:
        while True:
            time.sleep(86400)  # Sleep for a day
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        server.stop(grace=5)


if __name__ == "__main__":
    main()
