"""Main entry point for YouTube Collector Service."""
import sys
import asyncio
import structlog
from config import config
from collector import YouTubeCollector

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


def get_monitored_channels() -> list:
    """
    Get list of YouTube channels to monitor.
    
    This should be replaced with database query in production.
    For now, reads from environment variable.
    
    Returns:
        List of channel IDs
    """
    import os
    channels_str = os.getenv("YOUTUBE_CHANNELS", "")
    if not channels_str:
        logger.warning("no_channels_configured", message="Set YOUTUBE_CHANNELS environment variable")
        return []
    
    # Parse comma-separated channel IDs
    channels = [ch.strip() for ch in channels_str.split(",") if ch.strip()]
    return channels


async def main():
    """Run the YouTube Collector Service."""
    # Validate configuration
    if not config.validate():
        logger.error(
            "configuration_invalid",
            message="YOUTUBE_API_KEY must be set"
        )
        sys.exit(1)
    
    # Get channels to monitor
    channels = get_monitored_channels()
    if not channels:
        logger.error("no_channels_to_monitor")
        sys.exit(1)
    
    logger.info(
        "starting_youtube_collector",
        channel_count=len(channels),
        poll_interval=config.POLL_INTERVAL_SECONDS,
        transcription_enabled=config.ENABLE_TRANSCRIPTION,
        rabbitmq_host=config.RABBITMQ_HOST,
        exchange=config.RABBITMQ_EXCHANGE
    )
    
    # Create collector
    collector = YouTubeCollector()
    
    try:
        # Run polling loop
        await collector.run_polling_loop(channels)
    except KeyboardInterrupt:
        logger.info("shutdown_requested")
    except Exception as e:
        logger.error("collector_error", error=str(e))
        sys.exit(1)
    finally:
        collector.close()
        logger.info("youtube_collector_stopped")


if __name__ == "__main__":
    asyncio.run(main())
