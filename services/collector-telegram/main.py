"""
Главный файл Telegram Collector Service
Точка входа приложения
"""

import asyncio
import signal
import sys
import structlog
from structlog.stdlib import LoggerFactory

from config import settings
from collector import TelegramCollector


# Настройка структурированного логирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class CollectorService:
    """Основной класс сервиса коллектора"""
    
    def __init__(self):
        self.collector = None
        self.running = False
        self.mode = "polling"  # polling или monitoring
        
    async def start(self):
        """Запуск сервиса"""
        logger.info(
            "service_starting",
            mode=self.mode,
            poll_interval=settings.poll_interval
        )
        
        try:
            # Инициализация коллектора
            self.collector = TelegramCollector()
            await self.collector.initialize()
            
            self.running = True
            
            # Запуск в выбранном режиме
            if self.mode == "monitoring":
                logger.info("starting_in_monitoring_mode")
                await self.collector.start_monitoring()
            else:
                logger.info("starting_in_polling_mode")
                await self.collector.run_polling_mode()
                
        except KeyboardInterrupt:
            logger.info("keyboard_interrupt_received")
            await self.stop()
        except Exception as e:
            logger.error("service_error", error=str(e), exc_info=True)
            await self.stop()
            sys.exit(1)
    
    async def stop(self):
        """Остановка сервиса"""
        if not self.running:
            return
        
        logger.info("service_stopping")
        self.running = False
        
        if self.collector:
            await self.collector.shutdown()
        
        logger.info("service_stopped")
    
    def handle_signal(self, signum, frame):
        """Обработка системных сигналов"""
        logger.info("signal_received", signal=signum)
        asyncio.create_task(self.stop())


async def main():
    """Главная функция"""
    logger.info(
        "telegram_collector_service_starting",
        version="1.0.0",
        log_level=settings.log_level
    )
    
    # Создание сервиса
    service = CollectorService()
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, service.handle_signal)
    signal.signal(signal.SIGTERM, service.handle_signal)
    
    # Запуск сервиса
    await service.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("application_terminated")
    except Exception as e:
        logger.error("application_error", error=str(e), exc_info=True)
        sys.exit(1)
