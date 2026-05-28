# Summarization Service

Сервис для автоматической суммаризации текста и NLP-обработки контента с использованием трансформерных моделей.

## 📋 Описание

Summarization Service является ключевым компонентом системы фильтрации контента. Он получает сырой контент из RabbitMQ, обрабатывает его с помощью NLP-моделей и отправляет обработанные данные для дальнейшего ранжирования.

### Основные функции

- **Суммаризация текста** - создание кратких пересказов публикаций
- **Анализ тональности** - определение эмоциональной окраски текста
- **Генерация эмбеддингов** - создание векторных представлений для семантического поиска
- **Извлечение тем** - определение ключевых тем и тегов

## 🏗️ Архитектура

```
RabbitMQ (raw.*)
       ↓
  [Consumer]
       ↓
  [NLP Processor]
    ├─ Summarization (mBART)
    ├─ Sentiment Analysis (RuBERT)
    ├─ Embedding Generation (RuBERT)
    └─ Topic Extraction
       ↓
  [Database]
       ↓
  [Publisher]
       ↓
RabbitMQ (processed.*)
```

## 🚀 Быстрый старт

### Предварительные требования

- Docker 20.10+
- Docker Compose 2.0+
- 4 GB RAM (минимум), 8 GB (рекомендуется)
- 10 GB свободного места (для моделей)

### Запуск через Docker Compose

```bash
# Запуск всей инфраструктуры
docker-compose up -d postgres rabbitmq

# Запуск Summarization Service
docker-compose up -d summarization-service

# Просмотр логов
docker-compose logs -f summarization-service
```

### Локальная разработка

```bash
# Переход в директорию сервиса
cd services/summarization-service

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Копирование конфигурации
cp .env.example .env

# Редактирование .env с вашими настройками
nano .env

# Запуск сервиса
python main.py
```

## ⚙️ Конфигурация

### Переменные окружения

#### RabbitMQ настройки

```env
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=admin
RABBITMQ_PASSWORD=admin_password
RABBITMQ_EXCHANGE=content_exchange
RABBITMQ_INPUT_ROUTING_KEY=raw.*
RABBITMQ_OUTPUT_ROUTING_KEY_PREFIX=processed
```

#### PostgreSQL настройки

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=content_filter_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password
```

#### NLP модели

```env
# Модель для суммаризации (русский язык)
SUMMARIZATION_MODEL=IlyaGusev/mbart_ru_sum_gazeta

# Модель для анализа тональности
SENTIMENT_MODEL=blanchefort/rubert-base-cased-sentiment

# Модель для генерации эмбеддингов
EMBEDDING_MODEL=DeepPavlov/rubert-base-cased
```

#### Параметры суммаризации

```env
DEFAULT_MAX_LENGTH=150      # Максимальная длина резюме (слова)
DEFAULT_MIN_LENGTH=50       # Минимальная длина резюме (слова)
NUM_BEAMS=4                 # Количество beams для генерации
LENGTH_PENALTY=2.0          # Штраф за длину

# Адаптивная суммаризация
VERY_INTERESTED_LENGTH=250  # Для очень интересного контента
INTERESTED_LENGTH=150       # Для интересного контента
MAYBE_LENGTH=75             # Для возможно интересного
NOT_INTERESTED_LENGTH=30    # Для неинтересного
```

#### Производительность

```env
USE_GPU=false               # Использовать GPU (требует CUDA)
MODEL_CACHE_DIR=./models    # Директория для кэша моделей
PREFETCH_COUNT=1            # Количество prefetch сообщений
BATCH_SIZE=1                # Размер батча для обработки
MAX_TEXT_LENGTH=2000        # Максимальная длина текста (слова)
```

## 📊 Используемые модели

### 1. Суммаризация: IlyaGusev/mbart_ru_sum_gazeta

- **Тип**: mBART (Multilingual BART)
- **Язык**: Русский
- **Размер**: ~600 MB
- **Назначение**: Генерация кратких пересказов новостных текстов

### 2. Анализ тональности: blanchefort/rubert-base-cased-sentiment

- **Тип**: RuBERT
- **Язык**: Русский
- **Размер**: ~700 MB
- **Классы**: negative, neutral, positive

### 3. Эмбеддинги: DeepPavlov/rubert-base-cased

- **Тип**: BERT
- **Язык**: Русский
- **Размер**: ~700 MB
- **Размерность**: 768

**Общий размер моделей**: ~2 GB

## 🔄 Поток данных

### Входящие сообщения (RabbitMQ)

**Exchange**: `content_exchange` (topic)  
**Routing Key**: `raw.*` (raw.telegram, raw.vk, raw.youtube)  
**Queue**: `raw_content_queue`

**Формат сообщения**:

```json
{
  "message_type": "raw_content",
  "platform": "telegram",
  "source_id": 123,
  "source_url": "https://t.me/channel_name",
  "content": {
    "text": "Текст публикации...",
    "author": "Автор канала",
    "published_at": "2026-05-27T10:00:00Z",
    "media_urls": [],
    "original_url": "https://t.me/channel_name/12345"
  },
  "timestamp": "2026-05-27T10:00:05Z"
}
```

### Исходящие сообщения (RabbitMQ)

**Exchange**: `content_exchange` (topic)  
**Routing Key**: `processed.{platform}`  
**Queue**: `processed_content_queue`

**Формат сообщения**:

```json
{
  "message_type": "processed_content",
  "content_id": 456,
  "source_id": 123,
  "platform": "telegram",
  "summary": "Краткое содержание публикации",
  "embedding": [0.1, 0.2, ...],  // 768 значений
  "sentiment": 0.75,
  "sentiment_label": "positive",
  "topic_tags": ["технологии", "AI"],
  "timestamp": "2026-05-27T10:01:00Z"
}
```

### База данных

Обработанный контент сохраняется в таблицу `content_units`:

```sql
CREATE TABLE content_units (
    content_id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL,
    published_at TIMESTAMP NOT NULL,
    text TEXT,
    author VARCHAR(255),
    topic_tags JSONB,
    sentiment FLOAT,
    relevance_score FLOAT,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🧪 Примеры использования

### Базовая суммаризация

```python
from nlp_processor import NLPProcessor

processor = NLPProcessor()

text = "Длинный текст публикации..."
result = processor.summarize(text, max_length=150)

print(result["summary"])
print(f"Compression: {result['compression_ratio']:.2f}")
```

### Адаптивная суммаризация

```python
# Для очень интересного контента
result = processor.adaptive_summarize(text, "very_interested")

# Для неинтересного контента (только заголовок)
result = processor.adaptive_summarize(text, "not_interested")
```

### Полная обработка

```python
result = processor.process_content(text)

print(f"Summary: {result['summary']}")
print(f"Sentiment: {result['sentiment_label']} ({result['sentiment_score']:.2f})")
print(f"Topics: {', '.join(result['topics'])}")
print(f"Embedding dimension: {len(result['embedding'])}")
```

## 📈 Производительность

### Время обработки (CPU)

- Суммаризация: ~2-5 секунд на текст
- Анализ тональности: ~0.5-1 секунда
- Генерация эмбеддинга: ~0.5-1 секунда
- **Общее время**: ~3-7 секунд на сообщение

### Время обработки (GPU)

- Суммаризация: ~0.5-1 секунда
- Анализ тональности: ~0.1-0.2 секунды
- Генерация эмбеддинга: ~0.1-0.2 секунды
- **Общее время**: ~0.7-1.5 секунды на сообщение

### Использование ресурсов

- **RAM**: 2-4 GB (зависит от размера моделей)
- **CPU**: 1-2 ядра (при активной обработке)
- **Disk**: ~2 GB (модели) + данные

## 🔍 Мониторинг

### Логи

Сервис использует структурированное логирование (JSON):

```json
{
  "event": "content_processed_successfully",
  "content_id": 456,
  "platform": "telegram",
  "summary_length": 142,
  "sentiment": "positive",
  "topics": ["технологии", "AI"],
  "timestamp": "2026-05-27T10:01:00Z",
  "level": "info"
}
```

### Ключевые события

- `nlp_processor_initialized` - Модели загружены
- `message_received` - Получено сообщение из RabbitMQ
- `processing_content` - Начало обработки
- `text_summarized` - Суммаризация завершена
- `sentiment_analyzed` - Анализ тональности завершен
- `embedding_generated` - Эмбеддинг создан
- `content_saved_to_database` - Сохранено в БД
- `processed_content_published` - Опубликовано в RabbitMQ

### Метрики для мониторинга

- Количество обработанных сообщений
- Среднее время обработки
- Процент успешных обработок
- Размер очереди `raw_content_queue`
- Использование памяти и CPU

## 🐛 Отладка

### Проверка подключения к RabbitMQ

```bash
docker exec content_filter_summarization_service python -c "
from rabbitmq_consumer import RabbitMQConsumer
consumer = RabbitMQConsumer(lambda x: True)
consumer.connect()
print('RabbitMQ connection successful')
consumer.close()
"
```

### Проверка подключения к PostgreSQL

```bash
docker exec content_filter_summarization_service python -c "
from database import DatabaseManager
db = DatabaseManager()
print('Database connection successful')
db.close()
"
```

### Тестирование NLP моделей

```bash
docker exec content_filter_summarization_service python -c "
from nlp_processor import NLPProcessor
processor = NLPProcessor()
result = processor.summarize('Это тестовый текст для проверки работы модели суммаризации.')
print(f'Summary: {result[\"summary\"]}')
"
```

### Просмотр логов

```bash
# Все логи
docker-compose logs summarization-service

# Последние 100 строк
docker-compose logs --tail=100 summarization-service

# В реальном времени
docker-compose logs -f summarization-service

# Фильтрация по уровню
docker-compose logs summarization-service | grep "error"
```

## ❗ Частые проблемы

### 1. Модели не загружаются

**Проблема**: `OSError: Can't load model`

**Решение**:
```bash
# Очистка кэша моделей
docker volume rm content-filter_nlp_models

# Перезапуск с пересборкой
docker-compose up -d --build summarization-service
```

### 2. Недостаточно памяти

**Проблема**: `RuntimeError: CUDA out of memory` или `MemoryError`

**Решение**:
```yaml
# В docker-compose.yml увеличить лимиты
deploy:
  resources:
    limits:
      memory: 8G
```

### 3. Медленная обработка

**Проблема**: Время обработки > 10 секунд

**Решение**:
- Включить GPU: `USE_GPU=true`
- Уменьшить `NUM_BEAMS` до 2
- Уменьшить `MAX_TEXT_LENGTH`
- Использовать более легкие модели

### 4. Сообщения не обрабатываются

**Проблема**: Очередь растет, но сообщения не обрабатываются

**Решение**:
```bash
# Проверить статус сервиса
docker-compose ps summarization-service

# Проверить логи на ошибки
docker-compose logs summarization-service | grep "error"

# Перезапустить сервис
docker-compose restart summarization-service
```

## 🔧 Разработка

### Структура проекта

```
summarization-service/
├── __init__.py              # Инициализация пакета
├── main.py                  # Точка входа приложения
├── config.py                # Конфигурация
├── nlp_processor.py         # NLP обработка
├── rabbitmq_consumer.py     # RabbitMQ consumer
├── rabbitmq_publisher.py    # RabbitMQ publisher
├── database.py              # Работа с БД
├── requirements.txt         # Python зависимости
├── Dockerfile               # Docker образ
├── .env.example            # Пример конфигурации
└── README.md               # Документация
```

### Добавление новой модели

1. Добавить модель в `config.py`:
```python
new_model: str = Field(default="model/name", description="Description")
```

2. Загрузить модель в `nlp_processor.py`:
```python
def _load_new_model(self):
    self.new_model = AutoModel.from_pretrained(settings.new_model)
```

3. Добавить метод обработки:
```python
def process_with_new_model(self, text: str):
    # Ваша логика
    pass
```

### Тестирование

```bash
# Установка зависимостей для тестирования
pip install pytest pytest-asyncio pytest-mock

# Запуск тестов
pytest tests/

# С покрытием
pytest --cov=. tests/
```

## 📚 Дополнительные ресурсы

- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [mBART Documentation](https://huggingface.co/docs/transformers/model_doc/mbart)
- [RuBERT Models](https://huggingface.co/DeepPavlov)
- [RabbitMQ Documentation](https://www.rabbitmq.com/documentation.html)
- [pgvector Documentation](https://github.com/pgvector/pgvector)

## 📝 Лицензия

Этот проект распространяется под лицензией MIT.

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста:

1. Форкните репозиторий
2. Создайте ветку для вашей функции
3. Закоммитьте изменения
4. Создайте Pull Request

---

**Версия**: 1.0.0  
**Последнее обновление**: 2026-05-27  
**Статус**: ✅ Готов к использованию
