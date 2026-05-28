-- ============================================
-- Инициализация базы данных
-- ============================================

-- Создание расширения pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Проверка установки расширения
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Создание схемы для приложения (для будущего использования)
CREATE SCHEMA IF NOT EXISTS content_filter;

-- Используем public schema для совместимости с SQLAlchemy
-- SET search_path TO public;

-- Вывод информации
SELECT 'PostgreSQL initialized successfully with pgvector extension' AS status;

-- ============================================
-- Применение основной схемы
-- ============================================
-- Примечание: Схема будет применена из schema.sql
-- Таблицы создаются в public schema для совместимости с SQLAlchemy моделями