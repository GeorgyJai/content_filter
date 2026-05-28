"""Main bot application"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from grpc_client import user_service_client
from feedback_client import feedback_service_client
from handlers import onboarding, settings as settings_handlers, feedback, bulk_import

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def on_startup():
    """Actions on bot startup"""
    logger.info("Bot is starting...")
    
    # Connect to User Service
    try:
        await user_service_client.connect()
        logger.info("Connected to User Service")
    except Exception as e:
        logger.error(f"Failed to connect to User Service: {e}")
        logger.warning("Bot will continue, but user operations may fail")
    
    # Connect to Feedback Service
    try:
        await feedback_service_client.connect()
        logger.info("Connected to Feedback Service")
    except Exception as e:
        logger.error(f"Failed to connect to Feedback Service: {e}")
        logger.warning("Bot will continue, but feedback operations may fail")


async def on_shutdown():
    """Actions on bot shutdown"""
    logger.info("Bot is shutting down...")
    
    # Close gRPC connections
    try:
        await user_service_client.close()
        logger.info("Disconnected from User Service")
    except Exception as e:
        logger.error(f"Error closing User Service connection: {e}")
    
    try:
        await feedback_service_client.close()
        logger.info("Disconnected from Feedback Service")
    except Exception as e:
        logger.error(f"Error closing Feedback Service connection: {e}")


async def main():
    """Main bot function"""
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(onboarding.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(feedback.router)
    dp.include_router(bulk_import.router)
    
    # Register startup/shutdown handlers
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
