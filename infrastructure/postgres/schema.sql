-- ============================================
-- Схема базы данных для системы фильтрации контента
-- ============================================

-- Использование public schema для совместимости с SQLAlchemy моделями
-- SET search_path TO public;

-- ============================================
-- Таблица: users
-- Описание: Пользователи системы
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL, -- telegram, vk, etc.
    telegram_id BIGINT UNIQUE, -- ID пользователя в Telegram
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для users
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_platform ON users(platform);

-- ============================================
-- Таблица: user_profiles
-- Описание: Профили и предпочтения пользователей
-- ============================================
CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    preferences JSONB DEFAULT '{}', -- JSON с предпочтениями пользователя
    interests_text TEXT, -- Текстовое описание интересов
    interests_embedding vector(768), -- Векторное представление интересов (ruBERT)
    digest_interval_hours INTEGER DEFAULT 24, -- Интервал доставки дайджестов
    digest_time TIME DEFAULT '09:00:00', -- Время доставки дайджеста
    retention_days INTEGER DEFAULT 7, -- Срок хранения дайджестов
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Индексы для user_profiles
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

-- ============================================
-- Таблица: content_sources
-- Описание: Источники контента (каналы, группы, блоги)
-- ============================================
CREATE TABLE IF NOT EXISTS content_sources (
    source_id SERIAL PRIMARY KEY,
    platform_type VARCHAR(50) NOT NULL, -- telegram, vk, youtube
    url VARCHAR(500) NOT NULL,
    source_name VARCHAR(255), -- Название источника
    topic VARCHAR(255), -- Основная тема
    publish_frequency VARCHAR(50), -- Частота публикаций
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(platform_type, url)
);

-- Индексы для content_sources
CREATE INDEX IF NOT EXISTS idx_content_sources_platform ON content_sources(platform_type);
CREATE INDEX IF NOT EXISTS idx_content_sources_active ON content_sources(is_active);

-- ============================================
-- Таблица: subscriptions
-- Описание: Подписки пользователей на источники (связь многие-ко-многим)
-- ============================================
CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES content_sources(source_id) ON DELETE CASCADE,
    interest_level VARCHAR(50) DEFAULT 'interested', -- very_interested, interested, maybe, not_interested
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, source_id)
);

-- Индексы для subscriptions
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_source_id ON subscriptions(source_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_source ON subscriptions(user_id, source_id);

-- ============================================
-- Таблица: content_units
-- Описание: Единицы контента (посты, видео, статьи)
-- ============================================
CREATE TABLE IF NOT EXISTS content_units (
    content_id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES content_sources(source_id) ON DELETE CASCADE,
    published_at TIMESTAMP NOT NULL,
    text TEXT, -- Текст публикации
    summary TEXT, -- Краткое содержание (сгенерированное)
    author VARCHAR(255), -- Автор публикации
    original_url VARCHAR(500), -- Ссылка на оригинал
    media_urls JSONB DEFAULT '[]', -- Массив ссылок на медиа
    topic_tags JSONB DEFAULT '[]', -- Массив тегов/тем
    sentiment FLOAT, -- Тональность (-1 до 1)
    relevance_score FLOAT, -- Общий скор релевантности
    embedding vector(768), -- Векторное представление (ruBERT embeddings)
    is_processed BOOLEAN DEFAULT FALSE, -- Флаг обработки NLP-сервисами
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для content_units
CREATE INDEX IF NOT EXISTS idx_content_units_source_id ON content_units(source_id);
CREATE INDEX IF NOT EXISTS idx_content_units_published_at ON content_units(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_units_is_processed ON content_units(is_processed);
CREATE INDEX IF NOT EXISTS idx_content_units_created_at ON content_units(created_at DESC);

-- Векторный индекс для поиска по схожести (IVFFlat)
-- Создается после накопления данных для лучшей производительности
-- CREATE INDEX IF NOT EXISTS idx_content_units_embedding ON content_units 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================
-- Таблица: digests
-- Описание: Сгенерированные дайджесты для пользователей
-- ============================================
CREATE TABLE IF NOT EXISTS digests (
    digest_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    formatted_text TEXT, -- Отформатированный текст дайджеста
    telegram_message_id BIGINT, -- ID сообщения в Telegram для удаления
    items_count INTEGER DEFAULT 0, -- Количество элементов в дайджесте
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для digests
CREATE INDEX IF NOT EXISTS idx_digests_user_id ON digests(user_id);
CREATE INDEX IF NOT EXISTS idx_digests_created_at ON digests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_digests_period ON digests(period_start, period_end);

-- ============================================
-- Таблица: digest_items
-- Описание: Элементы дайджеста (связь дайджестов с контентом)
-- ============================================
CREATE TABLE IF NOT EXISTS digest_items (
    item_id SERIAL PRIMARY KEY,
    digest_id INTEGER NOT NULL REFERENCES digests(digest_id) ON DELETE CASCADE,
    content_id INTEGER NOT NULL REFERENCES content_units(content_id) ON DELETE CASCADE,
    annotation TEXT, -- Аннотация для этого элемента
    rank INTEGER NOT NULL, -- Позиция в дайджесте (1 = самый релевантный)
    relevance_score FLOAT, -- Скор релевантности для пользователя
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(digest_id, content_id)
);

-- Индексы для digest_items
CREATE INDEX IF NOT EXISTS idx_digest_items_digest_id ON digest_items(digest_id);
CREATE INDEX IF NOT EXISTS idx_digest_items_content_id ON digest_items(content_id);
CREATE INDEX IF NOT EXISTS idx_digest_items_rank ON digest_items(digest_id, rank);

-- ============================================
-- Таблица: feedback
-- Описание: Обратная связь пользователей о контенте
-- ============================================
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    content_id INTEGER NOT NULL REFERENCES content_units(content_id) ON DELETE CASCADE,
    reaction VARCHAR(50) NOT NULL, -- relevant, not_relevant, saved, hidden
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, content_id, reaction)
);

-- Индексы для feedback
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_content_id ON feedback(content_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_content ON feedback(user_id, content_id);
CREATE INDEX IF NOT EXISTS idx_feedback_reaction ON feedback(reaction);

-- ============================================
-- Таблица: quality_ratings
-- Описание: Оценки качества цифрового потребления (Release 3)
-- ============================================
CREATE TABLE IF NOT EXISTS quality_ratings (
    rating_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    digest_id INTEGER REFERENCES digests(digest_id) ON DELETE SET NULL,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
    comment TEXT, -- Опциональный комментарий
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для quality_ratings
CREATE INDEX IF NOT EXISTS idx_quality_ratings_user_id ON quality_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_quality_ratings_digest_id ON quality_ratings(digest_id);
CREATE INDEX IF NOT EXISTS idx_quality_ratings_created_at ON quality_ratings(created_at DESC);

-- ============================================
-- Таблица: user_interests_history
-- Описание: История изменений интересов пользователя для обучения
-- ============================================
CREATE TABLE IF NOT EXISTS user_interests_history (
    history_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    interests_embedding vector(768),
    feedback_count INTEGER DEFAULT 0, -- Количество обратной связи на момент обновления
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для user_interests_history
CREATE INDEX IF NOT EXISTS idx_user_interests_history_user_id ON user_interests_history(user_id);
CREATE INDEX IF NOT EXISTS idx_user_interests_history_created_at ON user_interests_history(created_at DESC);

-- ============================================
-- Функции и триггеры
-- ============================================

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_sources_updated_at
    BEFORE UPDATE ON content_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_units_updated_at
    BEFORE UPDATE ON content_units
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Представления (Views)
-- ============================================

-- Представление: Активные подписки с информацией об источниках
CREATE OR REPLACE VIEW active_subscriptions AS
SELECT 
    s.subscription_id,
    s.user_id,
    s.source_id,
    s.interest_level,
    s.subscribed_at,
    cs.platform_type,
    cs.url,
    cs.source_name,
    cs.topic
FROM subscriptions s
JOIN content_sources cs ON s.source_id = cs.source_id
WHERE cs.is_active = TRUE;

-- Представление: Статистика пользователей
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    u.user_id,
    u.username,
    COUNT(DISTINCT s.source_id) as subscriptions_count,
    COUNT(DISTINCT d.digest_id) as digests_count,
    COUNT(DISTINCT f.feedback_id) as feedback_count,
    AVG(qr.rating) as avg_quality_rating,
    MAX(d.created_at) as last_digest_at
FROM users u
LEFT JOIN subscriptions s ON u.user_id = s.user_id
LEFT JOIN digests d ON u.user_id = d.user_id
LEFT JOIN feedback f ON u.user_id = f.user_id
LEFT JOIN quality_ratings qr ON u.user_id = qr.user_id
GROUP BY u.user_id, u.username;

-- Представление: Популярные источники
CREATE OR REPLACE VIEW popular_sources AS
SELECT 
    cs.source_id,
    cs.platform_type,
    cs.source_name,
    cs.url,
    COUNT(DISTINCT s.user_id) as subscribers_count,
    COUNT(DISTINCT cu.content_id) as content_count
FROM content_sources cs
LEFT JOIN subscriptions s ON cs.source_id = s.source_id
LEFT JOIN content_units cu ON cs.source_id = cu.source_id
WHERE cs.is_active = TRUE
GROUP BY cs.source_id, cs.platform_type, cs.source_name, cs.url
ORDER BY subscribers_count DESC;

-- ============================================
-- Комментарии к таблицам
-- ============================================

COMMENT ON TABLE users IS 'Пользователи системы';
COMMENT ON TABLE user_profiles IS 'Профили и предпочтения пользователей';
COMMENT ON TABLE content_sources IS 'Источники контента (каналы, группы, блоги)';
COMMENT ON TABLE subscriptions IS 'Подписки пользователей на источники';
COMMENT ON TABLE content_units IS 'Единицы контента (посты, видео, статьи)';
COMMENT ON TABLE digests IS 'Сгенерированные дайджесты для пользователей';
COMMENT ON TABLE digest_items IS 'Элементы дайджеста';
COMMENT ON TABLE feedback IS 'Обратная связь пользователей о контенте';
COMMENT ON TABLE quality_ratings IS 'Оценки качества цифрового потребления';
COMMENT ON TABLE user_interests_history IS 'История изменений интересов пользователя';

-- ============================================
-- Начальные данные для тестирования (опционально)
-- ============================================

-- Вставка тестового пользователя (закомментировано для production)
-- INSERT INTO users (username, platform, telegram_id) 
-- VALUES ('test_user', 'telegram', 123456789)
-- ON CONFLICT (telegram_id) DO NOTHING;

-- ============================================
-- Информация о завершении
-- ============================================

SELECT 'Database schema created successfully!' AS status;
SELECT 'Total tables created: ' || COUNT(*) AS tables_count 
FROM information_schema.tables 
WHERE table_schema = 'content_filter';
