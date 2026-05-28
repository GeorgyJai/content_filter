"""
Точка входа для Ranking Service
"""
import logging
import sys
import time

from grpc_server import serve
from config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def wait_for_dependencies():
    """Ожидание готовности зависимостей (PostgreSQL)"""
    import psycopg2
    
    max_retries = 30
    retry_interval = 2
    
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            conn.close()
            logger.info("Successfully connected to PostgreSQL")
            return True
        except psycopg2.OperationalError as e:
            logger.warning(f"Waiting for PostgreSQL... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_interval)
    
    logger.error("Failed to connect to PostgreSQL after maximum retries")
    return False


def main():
    """Главная функция"""
    logger.info("=" * 60)
    logger.info("Starting Ranking Service")
    logger.info("=" * 60)
    logger.info(f"Configuration:")
    logger.info(f"  - Database: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")
    logger.info(f"  - gRPC Port: {config.GRPC_PORT}")
    logger.info(f"  - Model: {config.MODEL_NAME}")
    logger.info(f"  - Embedding Dimension: {config.EMBEDDING_DIM}")
    logger.info("=" * 60)
    
    # Ожидание готовности зависимостей
    if not wait_for_dependencies():
        logger.error("Failed to initialize dependencies. Exiting...")
        sys.exit(1)
    
    # Запуск gRPC сервера
    try:
        serve()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
