# Ranking Service

Сервис ранжирования и векторного поиска контента на основе машинного обучения.

## Описание

Ranking Service отвечает за:
- Генерацию векторных представлений (embeddings) текста с использованием BERT
- Ранжирование контента по релевантности для пользователя
- Векторный поиск похожего контента
- Обновление профиля интересов пользователя на основе обратной связи

## Технологии

- **Python 3.11+**
- **gRPC** - для межсервисного взаимодействия
- **PostgreSQL + pgvector** - для хранения и поиска векторов
- **Transformers (Hugging Face)** - для работы с BERT моделями
- **PyTorch** - для работы с нейронными сетями
- **DeepPavlov/rubert-base-cased** - предобученная модель для русского языка

## Архитектура

```
ranking-service/
├── __init__.py              # Инициализация пакета
├── config.py                # Конфигурация сервиса
├── database.py              # Работа с PostgreSQL + pgvector
├── embedding_generator.py   # Генерация эмбеддингов с BERT
├── ranker.py                # Логика ранжирования
├── grpc_server.py           # gRPC сервер
├── main.py                  # Точка входа
├── requirements.txt         # Зависимости Python
├── Dockerfile               # Docker образ
└── README.md                # Документация
```

## Основные компоненты

### 1. Embedding Generator
Генерирует векторные представления текста размерностью 768 с использованием ruBERT:
- Поддержка батч-обработки
- Автоматическое использование GPU если доступен
- Вычисление косинусного сходства

### 2. Content Ranker
Ранжирует контент на основе релевантности:
- Сравнение эмбеддингов контента с интересами пользователя
- Векторный поиск похожего контента
- Обновление профиля пользователя на основе обратной связи

### 3. Database Module
Работа с PostgreSQL и pgvector:
- Хранение и извлечение эмбеддингов
- Векторный поиск с использованием косинусного расстояния
- Управление профилями пользователей

## gRPC API

### GenerateEmbedding
Генерация эмбеддинга для текста.

**Request:**
```protobuf
message GenerateEmbeddingRequest {
    string text = 1;
}
```

**Response:**
```protobuf
message EmbeddingResponse {
    repeated float embedding = 1;
    bool success = 2;
    string message = 3;
}
```

### RankContentForUser
Ранжирование контента для пользователя.

**Request:**
```protobuf
message RankContentRequest {
    int32 user_id = 1;
    repeated int32 content_ids = 2;
    optional int32 limit = 3;
}
```

**Response:**
```protobuf
message RankedContentResponse {
    repeated RankedContent items = 1;
    bool success = 2;
    string message = 3;
}
```

### FindSimilarContent
Поиск похожего контента.

**Request:**
```protobuf
message FindSimilarContentRequest {
    int32 content_id = 1;
    optional int32 limit = 2;
    optional float min_similarity = 3;
}
```

**Response:**
```protobuf
message SimilarContentResponse {
    repeated SimilarContent items = 1;
    bool success = 2;
    string message = 3;
}
```

### UpdateUserInterestsFromFeedback
Обновление интересов пользователя на основе обратной связи.

**Request:**
```protobuf
message UpdateInterestsRequest {
    int32 user_id = 1;
    repeated FeedbackItem feedback_items = 2;
}
```

**Response:**
```protobuf
message UpdateInterestsResponse {
    repeated float new_interests_embedding = 1;
    bool success = 2;
    string message = 3;
}
```

## Конфигурация

Переменные окружения (см. `.env.example`):

### Database
- `DB_HOST` - хост PostgreSQL (по умолчанию: postgres)
- `DB_PORT` - порт PostgreSQL (по умолчанию: 5432)
- `DB_NAME` - имя базы данных (по умолчанию: content_filter_db)
- `DB_USER` - пользователь БД (по умолчанию: postgres)
- `DB_PASSWORD` - пароль БД (по умолчанию: postgres)

### gRPC Server
- `GRPC_PORT` - порт gRPC сервера (по умолчанию: 50053)

### Model
- `MODEL_NAME` - название модели (по умолчанию: DeepPavlov/rubert-base-cased)
- `EMBEDDING_DIM` - размерность эмбеддингов (по умолчанию: 768)
- `MAX_LENGTH` - максимальная длина текста (по умолчанию: 512)

### Ranking
- `DEFAULT_LIMIT` - количество результатов по умолчанию (по умолчанию: 10)
- `MIN_SIMILARITY` - минимальная схожесть (по умолчанию: 0.5)

### Feedback Learning
- `FEEDBACK_WEIGHT` - вес обратной связи (по умолчанию: 0.3)
- `RELEVANT_BOOST` - усиление для релевантного контента (по умолчанию: 1.0)
- `NOT_RELEVANT_PENALTY` - штраф за нерелевантный контент (по умолчанию: -0.5)

## Запуск

### Локально

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Сгенерируйте gRPC код:
```bash
cd ../../shared/proto
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ranking_service.proto
```

3. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env
```

4. Запустите сервис:
```bash
python main.py
```

### Docker

```bash
docker build -t ranking-service .
docker run -p 50053:50053 --env-file .env ranking-service
```

### Docker Compose

Сервис автоматически запускается через docker-compose.yml в корне проекта.

## Алгоритм ранжирования

1. **Генерация эмбеддингов**: Текст преобразуется в векторное представление размерностью 768 с использованием ruBERT

2. **Вычисление релевантности**: Косинусное сходство между эмбеддингом контента и эмбеддингом интересов пользователя

3. **Сортировка**: Контент сортируется по убыванию релевантности

4. **Обучение на обратной связи**: 
   - Релевантный контент увеличивает вес соответствующих тем
   - Нерелевантный контент уменьшает вес
   - Используется взвешенное среднее для обновления профиля

## Векторный поиск

Использует pgvector для эффективного поиска похожего контента:
- Индекс IVFFlat для быстрого поиска
- Косинусное расстояние как метрика схожести
- Фильтрация по минимальной схожести

## Производительность

- **Генерация эмбеддинга**: ~50-100ms на CPU, ~10-20ms на GPU
- **Ранжирование 100 элементов**: ~200-300ms
- **Векторный поиск**: ~50-100ms (с индексом)

## Масштабирование

- Горизонтальное масштабирование через несколько инстансов
- Использование GPU для ускорения генерации эмбеддингов
- Кэширование эмбеддингов в БД
- Батч-обработка для повышения throughput

## Мониторинг

Логи включают:
- Время генерации эмбеддингов
- Количество ранжированных элементов
- Ошибки при работе с моделью
- Статистика обратной связи

## Зависимости

- PostgreSQL с расширением pgvector
- Доступ к интернету для загрузки модели (при первом запуске)
- ~2GB RAM для модели
- GPU опционально (для ускорения)

## Troubleshooting

### Модель не загружается
```bash
# Предварительная загрузка модели
python -c "from transformers import AutoModel; AutoModel.from_pretrained('DeepPavlov/rubert-base-cased')"
```

### Ошибка подключения к PostgreSQL
Проверьте:
- PostgreSQL запущен
- Расширение pgvector установлено
- Правильные credentials в .env

### Out of Memory
- Уменьшите MAX_LENGTH
- Используйте батч-обработку с меньшим размером батча
- Увеличьте RAM или используйте swap

## Разработка

### Тестирование
```bash
# Unit тесты
pytest tests/

# Интеграционные тесты
pytest tests/integration/
```

### Линтинг
```bash
pylint *.py
black *.py
```

## Лицензия

MIT

## Контакты

Для вопросов и предложений создавайте issue в репозитории проекта.
