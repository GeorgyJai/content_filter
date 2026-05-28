# VK Collector Service

Сервис для сбора контента из сообществ ВКонтакте через Callback API.

## Описание

VK Collector Service получает события от сообществ ВКонтакте через Callback API и публикует их в RabbitMQ для дальнейшей обработки.

## Возможности

- ✅ Прием webhook-событий от VK Callback API
- ✅ Обработка новых постов на стене сообщества
- ✅ Обработка репостов
- ✅ Извлечение медиа-контента (фото, видео, ссылки, документы)
- ✅ Проверка подписи запросов для безопасности
- ✅ Публикация в RabbitMQ с routing key `raw.vk`
- ✅ Структурированное логирование
- ✅ Health check endpoint

## Архитектура

```
VK Community → Callback API → VK Collector → RabbitMQ → Summarization Service
```

## Настройка VK Callback API

### 1. Создание приложения VK

1. Перейдите на https://vk.com/apps?act=manage
2. Создайте новое Standalone-приложение
3. Получите Access Token с правами доступа к сообществу

### 2. Настройка Callback API в сообществе

1. Откройте настройки сообщества → API → Callback API
2. Укажите адрес сервера: `http://your-domain.com/vk_callback`
3. Укажите Secret key (любая случайная строка)
4. Включите события:
   - Новая запись на стене (wall_post_new)
   - Новый репост записи (wall_repost)

### 3. Подтверждение сервера

При первом запросе VK отправит событие типа `confirmation`. Сервис автоматически ответит токеном подтверждения из переменной `VK_CONFIRMATION_TOKEN`.

## Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```bash
# VK API Configuration
VK_API_VERSION=5.131
VK_CONFIRMATION_TOKEN=your_confirmation_token_here  # Токен подтверждения из настроек Callback API
VK_SECRET_KEY=your_secret_key_here                  # Secret key из настроек Callback API
VK_ACCESS_TOKEN=your_vk_access_token_here           # Access token приложения (опционально)

# Server Configuration
HOST=0.0.0.0
PORT=8080

# RabbitMQ Configuration
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_EXCHANGE=content_exchange
RABBITMQ_ROUTING_KEY=raw.vk

# Logging
LOG_LEVEL=INFO
```

## Запуск

### Docker Compose (рекомендуется)

```bash
docker-compose up collector-vk
```

### Локальный запуск

```bash
cd services/collector-vk
pip install -r requirements.txt
python main.py
```

## API Endpoints

### POST /vk_callback

Webhook endpoint для приема событий от VK.

**Headers:**
- `X-VK-Signature` - Подпись запроса (проверяется автоматически)

**Request Body:**
```json
{
  "type": "wall_post_new",
  "object": {
    "id": 123,
    "owner_id": -123456789,
    "from_id": -123456789,
    "date": 1234567890,
    "text": "Текст поста",
    "attachments": [...]
  },
  "group_id": 123456789
}
```

**Response:**
```json
{
  "response": "ok"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "vk-collector"
}
```

## Формат сообщений в RabbitMQ

Сервис публикует сообщения в следующем формате:

```json
{
  "message_type": "raw_content",
  "platform": "vk",
  "source_id": 123456789,
  "source_url": "https://vk.com/public123456789",
  "content": {
    "post_id": "-123456789_123",
    "text": "Текст поста",
    "author_id": -123456789,
    "signer_id": null,
    "published_at": "2026-05-27T10:00:00",
    "media_urls": [
      "https://sun9-1.userapi.com/...",
      "https://vk.com/video-123456789_456123456"
    ],
    "original_url": "https://vk.com/wall-123456789_123",
    "likes_count": 42,
    "reposts_count": 5,
    "views_count": 1000
  },
  "timestamp": "2026-05-27T10:00:05.123456"
}
```

## Обработка медиа-контента

Сервис извлекает следующие типы медиа:

- **Фото** - URL самого большого размера
- **Видео** - Ссылка на видео в формате `https://vk.com/video{owner_id}_{video_id}`
- **Ссылки** - URL из вложения типа `link`
- **Документы** - URL документа

## Безопасность

### Проверка подписи

Все запросы от VK подписываются с использованием Secret Key. Сервис автоматически проверяет подпись в заголовке `X-VK-Signature`.

Если `VK_SECRET_KEY` не настроен, проверка подписи пропускается (не рекомендуется для production).

### Рекомендации

1. Всегда используйте HTTPS для webhook URL
2. Настройте Secret Key и храните его в безопасности
3. Используйте firewall для ограничения доступа к webhook endpoint
4. Регулярно ротируйте Access Token

## Мониторинг

### Логи

Сервис использует структурированное логирование в формате JSON:

```json
{
  "event": "wall_post_processed",
  "post_id": "-123456789_123",
  "text_length": 256,
  "media_count": 2,
  "timestamp": "2026-05-27T10:00:00.123456Z",
  "level": "info"
}
```

### Метрики

Основные события для мониторинга:
- `confirmation_requested` - Запрос подтверждения сервера
- `wall_post_processed` - Пост успешно обработан
- `wall_post_published` - Пост опубликован в RabbitMQ
- `invalid_signature` - Неверная подпись запроса
- `rabbitmq_connected` - Подключение к RabbitMQ
- `publish_failed` - Ошибка публикации в RabbitMQ

## Troubleshooting

### Проблема: VK не может подтвердить сервер

**Решение:**
1. Убедитесь, что сервис доступен по указанному URL
2. Проверьте, что `VK_CONFIRMATION_TOKEN` совпадает с токеном в настройках Callback API
3. Проверьте логи на наличие ошибок

### Проблема: События не приходят

**Решение:**
1. Проверьте, что события включены в настройках Callback API
2. Убедитесь, что Secret Key настроен правильно
3. Проверьте логи VK в настройках Callback API

### Проблема: Ошибка подключения к RabbitMQ

**Решение:**
1. Убедитесь, что RabbitMQ запущен
2. Проверьте настройки подключения в `.env`
3. Проверьте сетевую доступность RabbitMQ

## Разработка

### Структура проекта

```
collector-vk/
├── __init__.py           # Инициализация пакета
├── config.py             # Конфигурация
├── main.py               # Точка входа
├── webhook.py            # Обработчик webhook
├── rabbitmq_publisher.py # Публикация в RabbitMQ
├── requirements.txt      # Зависимости
├── Dockerfile           # Docker образ
├── .env.example         # Пример конфигурации
└── README.md            # Документация
```

### Тестирование

Для локального тестирования можно использовать ngrok:

```bash
# Запустите сервис локально
python main.py

# В другом терминале запустите ngrok
ngrok http 8080

# Используйте ngrok URL в настройках VK Callback API
```

## Интеграция с другими сервисами

### Summarization Service

Summarization Service подписывается на очередь с routing key `raw.vk` и обрабатывает сообщения от VK Collector.

### User Service

Для связи постов с пользователями системы используется `source_id` (ID сообщества VK).

## Лицензия

Часть проекта Content Filter System.
