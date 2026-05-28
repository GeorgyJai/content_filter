# Feedback Service

Сервис для управления обратной связью пользователей и оценками качества цифрового потребления.

## Функциональность

### Обратная связь о контенте
- Сохранение оценок контента (актуально/неактуально/сохранено/скрыто)
- Получение истории обратной связи пользователя
- Статистика по контенту
- Пакетное сохранение обратной связи

### Оценка качества (Release 3)
- Сохранение оценок качества дайджестов (1-10)
- История оценок пользователя
- Статистика по неделям
- Визуализация "цифрового сада"

## API (gRPC)

### Методы обратной связи

#### SaveFeedback
Сохранение одной оценки контента.

```protobuf
rpc SaveFeedback(SaveFeedbackRequest) returns (FeedbackResponse);
```

#### SaveBatchFeedback
Пакетное сохранение оценок.

```protobuf
rpc SaveBatchFeedback(SaveBatchFeedbackRequest) returns (BatchFeedbackResponse);
```

#### GetUserFeedback
Получение истории обратной связи пользователя.

```protobuf
rpc GetUserFeedback(GetUserFeedbackRequest) returns (UserFeedbackResponse);
```

#### GetContentFeedback
Получение статистики по контенту.

```protobuf
rpc GetContentFeedback(GetContentFeedbackRequest) returns (ContentFeedbackResponse);
```

### Методы оценки качества

#### SaveQualityRating
Сохранение оценки качества дайджеста.

```protobuf
rpc SaveQualityRating(SaveQualityRatingRequest) returns (QualityRatingResponse);
```

#### GetUserQualityRatings
Получение истории оценок качества.

```protobuf
rpc GetUserQualityRatings(GetQualityRatingsRequest) returns (QualityRatingsResponse);
```

#### GetQualityStatistics
Получение статистики качества с разбивкой по неделям.

```protobuf
rpc GetQualityStatistics(GetQualityStatisticsRequest) returns (QualityStatisticsResponse);
```

## Типы реакций

- `relevant` - контент актуален для пользователя
- `not_relevant` - контент не актуален
- `saved` - контент сохранен для последующего чтения
- `hidden` - контент скрыт, не показывать подобное

## База данных

### Таблица feedback
```sql
CREATE TABLE feedback (
    feedback_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    content_id INTEGER REFERENCES content_units(content_id),
    reaction VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, content_id, reaction)
);
```

### Таблица quality_ratings
```sql
CREATE TABLE quality_ratings (
    rating_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    digest_id INTEGER REFERENCES digests(digest_id),
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 10),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Конфигурация

Переменные окружения (см. `.env.example`):

- `GRPC_PORT` - порт gRPC сервера (по умолчанию 50055)
- `POSTGRES_HOST` - хост PostgreSQL
- `POSTGRES_PORT` - порт PostgreSQL
- `POSTGRES_DB` - имя базы данных
- `POSTGRES_USER` - пользователь БД
- `POSTGRES_PASSWORD` - пароль БД
- `LOG_LEVEL` - уровень логирования

## Запуск

### Локально
```bash
# Установка зависимостей
pip install -r requirements.txt

# Генерация gRPC кода
python -m grpc_tools.protoc \
    -I../../shared/proto \
    --python_out=../../shared/proto \
    --grpc_python_out=../../shared/proto \
    ../../shared/proto/feedback_service.proto

# Запуск сервиса
python main.py
```

### Docker
```bash
docker build -t feedback-service .
docker run -p 50055:50055 --env-file .env feedback-service
```

### Docker Compose
```bash
docker-compose up feedback-service
```

## Интеграция

### Bot Service
Bot Service использует Feedback Service для:
- Сохранения оценок контента от пользователей
- Получения статистики обратной связи
- Сохранения оценок качества дайджестов
- Отображения "цифрового сада"

### Ranking Service
Ranking Service использует данные обратной связи для:
- Обновления профиля интересов пользователя
- Улучшения ранжирования контента
- Персонализации рекомендаций

## Мониторинг

Сервис логирует:
- Все операции сохранения обратной связи
- Запросы статистики
- Ошибки базы данных
- gRPC вызовы

## Разработка

### Добавление новых типов реакций
1. Обновить proto файл
2. Добавить обработку в `database.py`
3. Обновить валидацию в `grpc_server.py`
4. Обновить Bot Service handlers

### Тестирование
```bash
# Unit тесты
pytest tests/

# Интеграционные тесты
pytest tests/integration/
```

## Производительность

- Использует connection pooling для PostgreSQL
- Поддерживает пакетное сохранение обратной связи
- Индексы на часто используемых полях
- Кэширование статистики (планируется)

## Безопасность

- Валидация всех входных данных
- Проверка диапазона оценок (1-10)
- Уникальные ограничения для предотвращения дубликатов
- Логирование всех операций
