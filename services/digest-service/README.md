# Digest Service

Сервис генерации персонализированных дайджестов контента с автоматическим планировщиком.

## Описание

Digest Service отвечает за:
- 📊 Генерацию персонализированных дайджестов для пользователей
- ⏰ Автоматическую отправку дайджестов по расписанию
- 🎯 Ранжирование контента по релевантности
- 📝 Форматирование дайджестов для отправки пользователям
- 💾 Сохранение истории дайджестов в БД

## Архитектура

### Основные компоненты

1. **gRPC Server** (`grpc_server.py`)
   - Предоставляет API для генерации и получения дайджестов
   - Методы: `GenerateDigest`, `GetDigest`

2. **Scheduler** (`scheduler.py`)
   - Автоматически проверяет, каким пользователям нужны дайджесты
   - Генерирует и отправляет дайджесты по расписанию
   - Использует APScheduler для периодических задач

3. **Digest Generator** (`digest_generator.py`)
   - Логика генерации дайджестов
   - Интеграция с Ranking Service для ранжирования
   - Форматирование дайджестов

4. **Database Manager** (`database.py`)
   - Работа с PostgreSQL
   - Модели: Digest, DigestItem, ContentUnit, User, etc.
   - Запросы для получения контента и сохранения дайджестов

## Установка и запуск

### Через Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск только Digest Service
docker-compose up -d digest-service

# Просмотр логов
docker-compose logs -f digest-service
```

### Локальный запуск

```bash
# Установка зависимостей
cd services/digest-service
pip install -r requirements.txt

# Генерация proto файлов
python -m grpc_tools.protoc \
    -I../../shared/proto \
    --python_out=../../shared/proto \
    --grpc_python_out=../../shared/proto \
    ../../shared/proto/digest_service.proto

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл

# Запуск сервиса
python main.py
```

## Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DB_HOST` | Хост PostgreSQL | `postgres` |
| `DB_PORT` | Порт PostgreSQL | `5432` |
| `DB_NAME` | Имя базы данных | `content_filter_db` |
| `DB_USER` | Пользователь БД | `postgres` |
| `DB_PASSWORD` | Пароль БД | `postgres_password` |
| `GRPC_PORT` | Порт gRPC сервера | `50052` |
| `GRPC_MAX_WORKERS` | Макс. воркеров gRPC | `10` |
| `USER_SERVICE_HOST` | Хост User Service | `user-service` |
| `USER_SERVICE_PORT` | Порт User Service | `50051` |
| `RANKING_SERVICE_HOST` | Хост Ranking Service | `ranking-service` |
| `RANKING_SERVICE_PORT` | Порт Ranking Service | `50053` |
| `SCHEDULER_ENABLED` | Включить планировщик | `true` |
| `SCHEDULER_CHECK_INTERVAL` | Интервал проверки (сек) | `60` |
| `DEFAULT_DIGEST_INTERVAL_HOURS` | Интервал дайджестов (часы) | `8` |
| `DEFAULT_MAX_ITEMS` | Макс. элементов в дайджесте | `10` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

## API

### gRPC методы

#### GenerateDigest

Генерирует новый дайджест для пользователя.

**Request:**
```protobuf
message GenerateDigestRequest {
    int32 user_id = 1;
    string period_start = 2;  // optional
    string period_end = 3;    // optional
}
```

**Response:**
```protobuf
message DigestResponse {
    int32 digest_id = 1;
    repeated DigestItem items = 2;
    string formatted_text = 3;
}
```

**Пример использования (Python):**
```python
import grpc
from shared.proto import digest_service_pb2, digest_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50052')
stub = digest_service_pb2_grpc.DigestServiceStub(channel)

request = digest_service_pb2.GenerateDigestRequest(user_id=1)
response = stub.GenerateDigest(request)

print(f"Digest ID: {response.digest_id}")
print(f"Items: {len(response.items)}")
print(f"Text:\n{response.formatted_text}")
```

#### GetDigest

Получает существующий дайджест по ID.

**Request:**
```protobuf
message GetDigestRequest {
    int32 digest_id = 1;
}
```

**Response:**
```protobuf
message DigestResponse {
    int32 digest_id = 1;
    repeated DigestItem items = 2;
    string formatted_text = 3;
}
```

## Планировщик

### Как работает

1. **Проверка расписаний** - каждые N секунд (по умолчанию 60)
2. **Определение пользователей** - кому нужны дайджесты
3. **Генерация дайджестов** - для каждого пользователя
4. **Отправка** - через Bot Service

### Логика определения времени отправки

Дайджест отправляется пользователю, если:
- Прошло N часов с последнего дайджеста (настраивается в профиле)
- Или это первый дайджест пользователя

### Настройка интервала для пользователя

Интервал хранится в `user_profiles.preferences`:
```json
{
  "digest_interval_hours": 8
}
```

Возможные значения: 4, 8, 12, 24 часа.

## Формат дайджеста

Дайджест форматируется в HTML для Telegram:

```
📰 Ваш персональный дайджест
📅 Период: 27.05.2026 10:00 - 27.05.2026 18:00
📊 Найдено материалов: 10

────────────────────────────────────────

1. ✈️ технологии, AI, инновации
Краткое содержание публикации о новых технологиях...

🔗 Читать полностью | 📡 https://t.me/tech_channel
/feedback_456

────────────────────────────────────────

2. 🔵 бизнес, стартапы
Новости о стартапах и инвестициях...

🔗 Читать полностью | 📡 https://vk.com/business
/feedback_457

...

💡 Оцените качество дайджеста: /rate
```

## База данных

### Таблицы

#### digests
```sql
CREATE TABLE digests (
    digest_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    telegram_message_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### digest_items
```sql
CREATE TABLE digest_items (
    item_id SERIAL PRIMARY KEY,
    digest_id INTEGER REFERENCES digests(digest_id),
    content_id INTEGER REFERENCES content_units(content_id),
    annotation TEXT,
    rank INTEGER,
    UNIQUE(digest_id, content_id)
);
```

## Мониторинг

### Логи

Сервис логирует:
- Запуск/остановку компонентов
- Генерацию дайджестов
- Ошибки и предупреждения
- Статистику (количество пользователей, элементов)

### Healthcheck

Docker healthcheck проверяет доступность gRPC сервера:
```bash
docker exec digest-service python -c "import grpc; channel = grpc.insecure_channel('localhost:50052'); channel.close()"
```

## Интеграция с другими сервисами

### User Service
- Получение информации о пользователях
- Получение подписок пользователя

### Ranking Service
- Ранжирование контента по релевантности
- Учет обратной связи пользователя

### Bot Service
- Отправка дайджестов пользователям
- Обработка команд (/rate, /feedback)

## Разработка

### Структура проекта

```
services/digest-service/
├── __init__.py
├── config.py              # Конфигурация
├── database.py            # Модели и работа с БД
├── digest_generator.py    # Логика генерации дайджестов
├── scheduler.py           # Планировщик
├── grpc_server.py         # gRPC сервер
├── main.py                # Точка входа
├── requirements.txt       # Зависимости
├── Dockerfile             # Docker образ
├── .env.example           # Пример конфигурации
└── README.md              # Документация
```

### Добавление новых функций

1. **Новый формат дайджеста**
   - Редактируйте `digest_generator.format_digest_text()`

2. **Новая логика ранжирования**
   - Редактируйте `digest_generator._rank_content()`

3. **Новые триггеры отправки**
   - Редактируйте `scheduler.check_and_generate_digests()`

## Тестирование

### Ручная генерация дайджеста

```python
from digest_generator import digest_generator

# Генерация дайджеста для пользователя
digest_data = digest_generator.generate_digest(user_id=1)
print(digest_data)

# Форматирование
text = digest_generator.format_digest_text(digest_data)
print(text)
```

### Тестирование планировщика

```python
from scheduler import digest_scheduler

# Запуск планировщика
digest_scheduler.start()

# Ручная генерация
digest_data = digest_scheduler.trigger_manual_generation(user_id=1)
```

## Troubleshooting

### Дайджесты не генерируются

1. Проверьте, включен ли планировщик: `SCHEDULER_ENABLED=true`
2. Проверьте логи: `docker-compose logs digest-service`
3. Убедитесь, что у пользователей есть подписки
4. Проверьте наличие нового контента в БД

### Ошибки подключения к Ranking Service

1. Проверьте, запущен ли Ranking Service
2. Проверьте настройки: `RANKING_SERVICE_HOST` и `RANKING_SERVICE_PORT`
3. Сервис продолжит работу без ранжирования (хронологический порядок)

### Пустые дайджесты

1. Проверьте, есть ли новый контент за период
2. Проверьте, обработан ли контент (есть ли summary и embedding)
3. Проверьте подписки пользователя

## Лицензия

Часть проекта Content Filter System.

## Контакты

Для вопросов и предложений создавайте issue в репозитории проекта.
