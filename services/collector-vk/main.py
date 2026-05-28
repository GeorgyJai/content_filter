"""Main entry point for VK Collector Service."""
import sys
import structlog
import uvicorn
from config import config

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


def main():
    """Run the VK Collector Service."""
    # Validate configuration
    if not config.validate():
        logger.error(
            "configuration_invalid",
            message="VK_CONFIRMATION_TOKEN and VK_SECRET_KEY must be set"
        )
        sys.exit(1)
    
    logger.info(
        "starting_vk_collector",
        host=config.HOST,
        port=config.PORT,
        rabbitmq_host=config.RABBITMQ_HOST,
        exchange=config.RABBITMQ_EXCHANGE
    )
    
    # Import app here to ensure logging is configured first
    from webhook import create_app
    app = create_app()
    
    # Run server
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
