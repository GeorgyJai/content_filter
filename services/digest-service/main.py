"""
Главный модуль Digest Service
Запускает gRPC сервер и планировщик
"""

import logging
import asyncio
import signal
import sys
from threading import Thread

from config import config
from grpc_server import serve
from scheduler import digest_scheduler

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class DigestService:
    """Главный класс сервиса дайджестов"""
    
    def __init__(self):
        self.grpc_server = None
        self.scheduler = digest_scheduler
        self.running = False
    
    def start(self):
        """Запуск сервиса"""
        logger.info("=" * 60)
        logger.info("Starting Digest Service")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  - Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
        logger.info(f"  - gRPC Port: {config.GRPC_PORT}")
        logger.info(f"  - Scheduler Enabled: {config.SCHEDULER_ENABLED}")
        logger.info(f"  - Check Interval: {config.SCHEDULER_CHECK_INTERVAL}s")
        logger.info(f"  - Default Digest Interval: {config.DEFAULT_DIGEST_INTERVAL_HOURS}h")
        logger.info("=" * 60)
        
        try:
            # Запускаем gRPC сервер в отдельном потоке
            self.grpc_server = serve()
            logger.info("gRPC server started successfully")
            
            # Запускаем планировщик
            if config.SCHEDULER_ENABLED:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
            else:
                logger.info("Scheduler is disabled")
            
            self.running = True
            logger.info("Digest Service is running")
            
            # Ожидаем завершения
            self.grpc_server.wait_for_termination()
            
        except Exception as e:
            logger.error(f"Error starting service: {e}", exc_info=True)
            self.stop()
            sys.exit(1)
    
    def stop(self):
        """Остановка сервиса"""
        if not self.running:
            return
        
        logger.info("Stopping Digest Service...")
        
        try:
            # Останавливаем планировщик
            if self.scheduler.is_running:
                self.scheduler.stop()
                logger.info("Scheduler stopped")
            
            # Останавливаем gRPC сервер
            if self.grpc_server:
                self.grpc_server.stop(grace=5)
                logger.info("gRPC server stopped")
            
            self.running = False
            logger.info("Digest Service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping service: {e}", exc_info=True)


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"Received signal {signum}")
    if service:
        service.stop()
    sys.exit(0)


# Глобальный экземпляр сервиса
service = None


def main():
    """Главная функция"""
    global service
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создаем и запускаем сервис
    service = DigestService()
    service.start()


if __name__ == '__main__':
    main()
