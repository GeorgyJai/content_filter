# Telegram Collector Service

Сервис для сбора контента из Telegram-каналов и отправки в RabbitMQ для дальнейшей обработки.

## 🎯 Назначение

Telegram Collector Service отвечает за:
- Мониторинг Telegram-каналов из базы данных
- Сбор новых публикаций из каналов
- Форматирование контента по схеме `RawContentMessage`
- Публикацию сообщений в RabbitMQ для обработки NLP-сервисами

## 🏗️ Архитектура

### Режимы работы

1. **Polling Mode (по умолчанию)** - Периодический опрос каналов
   - Получает список каналов из БД
   - Собирает новые сообщения с заданным интервалом
   - Подходит для большого количества каналов

2. **Monitoring Mode** - Мониторинг в реальном времени
   - Подписывается на события новых сообщений
   - Мгновенная обработка новых публикаций
   - Требует постоянного соединения

### Компоненты

- **collector.py** - Основная логика сбора контента
- **rabbitmq_publisher.py** - Публикация в RabbitMQ
- **config.py** - Конфигурация сервиса
- **main.py** - Точка входа приложения

## 📋 Требования

- Python 3.11+
- Telegram API credentials (API ID и API Hash)
- Доступ к PostgreSQL
- Доступ к RabbitMQ
- Авторизованная сессия Telegram

## 🚀 Быстрый старт

### 1. Получение Telegram API credentials

1. Перейдите на https://my.telegram.org/apps
2. Войдите с вашим номером телефона
3. Создайте новое приложение
4. Сохраните `api_id` и `api_hash`

### 2. Настройка окружения

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование .env с вашими данными
nano .env
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Первый запуск (авторизация)

При первом запуске необходимо авторизоваться в Telegram:

```bash
python main.py
```

Следуйте инструкциям для ввода кода подтверждения из Telegram.

### 5. Запуск в Docker

```bash
# Сборка образа
docker build -t telegram-collector .

# Запуск контейнера
docker run -d \
  --name telegram-collector \
  --env-file .env \
  -v $(pwd)/sessions:/app/sessions \
  telegram-collector
```

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `TELEGRAM_API_ID` | Telegram API ID | - |
| `TELEGRAM_API_HASH` | Telegram API Hash | - |
| `TELEGRAM_PHONE` | Номер телефона для авторизации | - |
| `TELEGRAM_SESSION_NAME` | Имя файла сессии | collector_session |
| `RABBITMQ_HOST` | Хост RabbitMQ | localhost |
| `RABBITMQ_PORT` | Порт RabbitMQ | 5672 |
| `RABBITMQ_USER` | Пользователь RabbitMQ | admin |
| `RABBITMQ_PASSWORD` | Пароль RabbitMQ | admin_password |
| `RABBITMQ_EXCHANGE` | Exchange для публикации | content_exchange |
| `RABBITMQ_ROUTING_KEY` | Routing key | raw.telegram |
| `POSTGRES_HOST` | Хост PostgreSQL | localhost |
| `POSTGRES_PORT` | Порт PostgreSQL | 5432 |
| `POSTGRES_DB` | Имя базы данных | content_filter_db |
| `POSTGRES_USER` | Пользователь БД | postgres |
| `POSTGRES_PASSWORD` | Пароль БД | postgres |
| `LOG_LEVEL` | Уровень логирования | INFO |
| `POLL_INTERVAL` | Интервал опроса (секунды) | 60 |
| `MAX_MESSAGES_PER_CHANNEL` | Макс. сообщений за опрос | 50 |

## 📊 Формат сообщений

Сервис публикует сообщения в формате `RawContentMessage`:

```json
{
  "message_type": "raw_content",
  "platform": "telegram",
  "source_id": 123,
  "source_url": "https://t.me/channel_name",
  "content": {
    "text": "Текст публикации",
    "author": "Автор канала",
    "published_at": "2026-05-27T10:00:00Z",
    "media_urls": [],
    "original_url": "https://t.me/channel_name/12345"
  },
  "timestamp": "2026-05-27T10:00:05Z"
}
```

## 🔍 Мониторинг

### Логи

Сервис использует структурированное логирование (JSON):

```bash
# Просмотр логов в Docker
docker logs -f telegram-collector

# Фильтрация по уровню
docker logs telegram-collector 2>&1 | grep ERROR
```

### Метрики

Логируемые события:
- `telegram_client_initialized` - Клиент инициализирован
- `sources_fetched` - Получен список источников
- `channel_collected` - Собраны сообщения из канала
- `message_published` - Сообщение опубликовано в RabbitMQ
- `polling_cycle_completed` - Цикл опроса завершен

## 🛠️ Разработка

### Структура проекта

```
collector-telegram/
├── __init__.py
├── main.py                    # Точка входа
├── collector.py               # Основная логика
├── rabbitmq_publisher.py      # RabbitMQ клиент
├── config.py                  # Конфигурация
├── requirements.txt           # Зависимости
├── Dockerfile                 # Docker образ
├── .env.example              # Пример конфигурации
└── README.md                 # Документация
```

### Запуск в режиме разработки

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск с отладкой
LOG_LEVEL=DEBUG python main.py
```

### Тестирование

```bash
# Проверка подключения к Telegram
python -c "from collector import TelegramCollector; import asyncio; asyncio.run(TelegramCollector().initialize())"

# Проверка подключения к RabbitMQ
python -c "from rabbitmq_publisher import RabbitMQPublisher; p = RabbitMQPublisher(); p.connect(); p.close()"
```

## 🔒 Безопасность

### Важные замечания

1. **Файл сессии** - Содержит авторизационные данные Telegram
   - Храните в безопасном месте
   - Не коммитьте в Git
   - Используйте volume в Docker

2. **API credentials** - Не публикуйте API ID и Hash
   - Используйте переменные окружения
   - Не храните в коде

3. **Rate limiting** - Telegram имеет ограничения
   - Не опрашивайте слишком часто
   - Обрабатывайте FloodWaitError
   - Используйте задержки между запросами

## 🐛 Отладка

### Частые проблемы

**Ошибка авторизации:**
```bash
# Удалите старую сессию и авторизуйтесь заново
rm collector_session.session
python main.py
```

**FloodWaitError:**
```
Telegram ограничивает частоту запросов. Увеличьте POLL_INTERVAL.
```

**Канал не найден:**
```
Проверьте, что канал публичный и URL корректный.
```

**RabbitMQ connection refused:**
```bash
# Проверьте, что RabbitMQ запущен
docker ps | grep rabbitmq

# Проверьте доступность порта
telnet localhost 5672
```

## 📝 Логирование

Примеры логов:

```json
{
  "event": "channel_collected",
  "channel": "example_channel",
  "count": 15,
  "last_message_id": 12345,
  "timestamp": "2026-05-27T10:00:00Z",
  "level": "info"
}
```

## 🔄 Интеграция

### Добавление источников

Источники добавляются через User Service или напрямую в БД:

```sql
INSERT INTO content_sources (platform_type, url, topic)
VALUES ('telegram', 'https://t.me/channel_name', 'технологии');
```

### Обработка сообщений

Опубликованные сообщения обрабатываются:
1. **Summarization Service** - Создание резюме
2. **Ranking Service** - Векторизация и ранжирование
3. **Digest Service** - Включение в дайджесты

## 📚 Дополнительные ресурсы

- [Telethon Documentation](https://docs.telethon.dev/)
- [Telegram API](https://core.telegram.org/api)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)

## 🤝 Вклад в разработку

При добавлении новых функций:
1. Следуйте существующему стилю кода
2. Добавляйте структурированное логирование
3. Обрабатывайте ошибки корректно
4. Обновляйте документацию

## 📄 Лицензия

Часть проекта Content Filter System.
