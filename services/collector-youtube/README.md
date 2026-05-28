# YouTube Collector Service

Сервис для сбора контента из YouTube каналов с опциональной транскрипцией видео.

## Возможности

- 🔄 Периодический опрос YouTube каналов (polling)
- 📹 Получение информации о новых видео через YouTube Data API
- 🎤 Опциональная транскрипция аудио в текст (Whisper)
- 📊 Отслеживание обработанных видео (PostgreSQL)
- 📨 Публикация контента в RabbitMQ
- 🔍 Извлечение метаданных (просмотры, лайки, комментарии)

## Архитектура

```
YouTube API → Collector → [Optional: Audio Download → Whisper] → RabbitMQ
                    ↓
              PostgreSQL (tracking)
```

## Требования

- Python 3.11+
- YouTube Data API Key
- RabbitMQ
- PostgreSQL
- FFmpeg (для транскрипции)

## Установка

### 1. Получение YouTube API Key

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите YouTube Data API v3
4. Создайте API Key в разделе "Credentials"

### 2. Настройка окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env и укажите:
# - YOUTUBE_API_KEY
# - YOUTUBE_CHANNELS (ID каналов через запятую)
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

## Конфигурация

### Основные параметры

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `YOUTUBE_API_KEY` | API ключ YouTube Data API | - |
| `YOUTUBE_CHANNELS` | ID каналов через запятую | - |
| `POLL_INTERVAL_SECONDS` | Интервал опроса (секунды) | 300 |
| `MAX_RESULTS_PER_CHANNEL` | Макс. видео за запрос | 10 |

### Транскрипция

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `ENABLE_TRANSCRIPTION` | Включить транскрипцию | false |
| `WHISPER_MODEL` | Модель Whisper (tiny/base/small/medium/large) | base |
| `TRANSCRIPTION_LANGUAGE` | Язык транскрипции | ru |

**Примечание**: Транскрипция требует значительных ресурсов:
- `tiny`: ~1 GB RAM, быстро, низкое качество
- `base`: ~1 GB RAM, средняя скорость, среднее качество
- `small`: ~2 GB RAM, медленнее, хорошее качество
- `medium`: ~5 GB RAM, медленно, отличное качество
- `large`: ~10 GB RAM, очень медленно, лучшее качество

## Использование

### Локальный запуск

```bash
python main.py
```

### Docker

```bash
# Сборка образа
docker build -t collector-youtube .

# Запуск контейнера
docker run -d \
  --name collector-youtube \
  --env-file .env \
  collector-youtube
```

### Docker Compose

Сервис уже включен в `docker-compose.yml` корневой директории проекта.

```bash
# Запуск всех сервисов
docker-compose up -d

# Запуск только YouTube коллектора
docker-compose up -d collector-youtube

# Просмотр логов
docker-compose logs -f collector-youtube
```

## Как найти Channel ID

### Способ 1: Из URL канала

Если URL канала выглядит как `https://www.youtube.com/channel/UCxxxxxx`, то `UCxxxxxx` - это Channel ID.

### Способ 2: Через страницу канала

1. Откройте канал на YouTube
2. Откройте исходный код страницы (Ctrl+U)
3. Найдите `"channelId":"UCxxxxxx"`

### Способ 3: Через API

```python
from googleapiclient.discovery import build

youtube = build('youtube', 'v3', developerKey='YOUR_API_KEY')
request = youtube.channels().list(
    part="id",
    forUsername="username"  # или handle
)
response = request.execute()
print(response['items'][0]['id'])
```

## Формат сообщения RabbitMQ

```json
{
  "message_type": "raw_content",
  "platform": "youtube",
  "source_id": "UCxxxxxx",
  "source_url": "https://www.youtube.com/channel/UCxxxxxx",
  "content": {
    "video_id": "dQw4w9WgXcQ",
    "text": "Title\n\nDescription\n\n[Транскрипция]\n...",
    "title": "Video Title",
    "description": "Video description",
    "transcript": "Transcribed text...",
    "author": "Channel Name",
    "published_at": "2026-05-27T10:00:00Z",
    "original_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "thumbnail_url": "https://...",
    "duration": "PT5M30S",
    "view_count": 1000,
    "like_count": 100,
    "comment_count": 50,
    "tags": ["tag1", "tag2"]
  },
  "timestamp": "2026-05-27T10:01:00Z"
}
```

## База данных

Сервис создает таблицу `youtube_processed_videos` для отслеживания обработанных видео:

```sql
CREATE TABLE youtube_processed_videos (
    video_id VARCHAR(50) PRIMARY KEY,
    channel_id VARCHAR(50) NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    published_at TIMESTAMP
);
```

## Ограничения YouTube API

YouTube Data API имеет квоты:
- **10,000 единиц в день** (бесплатно)
- Запрос `search.list`: 100 единиц
- Запрос `videos.list`: 1 единица

**Расчет**: При опросе 10 каналов каждые 5 минут:
- 10 каналов × 100 единиц = 1,000 единиц за опрос
- 288 опросов в день (24ч × 60мин / 5мин)
- Но мы делаем только ~10 опросов в день при разумном использовании

## Мониторинг

### Логи

Сервис использует структурированное логирование (JSON):

```json
{
  "event": "video_processed",
  "video_id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "has_transcript": true,
  "timestamp": "2026-05-27T10:00:00Z"
}
```

### Метрики

- `channel_videos_fetched`: Количество найденных видео
- `video_processed`: Обработанное видео
- `audio_downloaded`: Скачанное аудио
- `audio_transcribed`: Транскрибированное аудио
- `message_published`: Опубликованное сообщение

## Troubleshooting

### Ошибка: "YOUTUBE_API_KEY must be set"

Убедитесь, что переменная окружения `YOUTUBE_API_KEY` установлена.

### Ошибка: "quotaExceeded"

Превышена дневная квота YouTube API. Подождите до следующего дня или увеличьте `POLL_INTERVAL_SECONDS`.

### Ошибка: "whisper_not_installed"

Установите Whisper: `pip install openai-whisper`

### Транскрипция работает медленно

- Используйте меньшую модель (`tiny` или `base`)
- Отключите транскрипцию: `ENABLE_TRANSCRIPTION=false`
- Используйте GPU (требует CUDA)

### Видео не обрабатываются

1. Проверьте, что Channel ID правильный
2. Проверьте логи: `docker-compose logs collector-youtube`
3. Убедитесь, что на канале есть новые видео
4. Проверьте подключение к RabbitMQ и PostgreSQL

## Разработка

### Структура проекта

```
collector-youtube/
├── __init__.py
├── config.py              # Конфигурация
├── collector.py           # Основная логика сбора
├── database.py            # Работа с PostgreSQL
├── rabbitmq_publisher.py  # Публикация в RabbitMQ
├── main.py               # Точка входа
├── requirements.txt      # Зависимости
├── Dockerfile           # Docker образ
├── .env.example         # Пример конфигурации
└── README.md           # Документация
```

### Тестирование

```bash
# Запуск с одним каналом для теста
YOUTUBE_CHANNELS=UCxxxxxx python main.py

# Проверка подключения к RabbitMQ
docker-compose exec rabbitmq rabbitmqctl list_queues

# Проверка базы данных
docker-compose exec postgres psql -U postgres -d content_filter_db \
  -c "SELECT * FROM youtube_processed_videos LIMIT 10;"
```

## Производительность

### Без транскрипции
- ~1-2 секунды на видео
- Минимальное использование ресурсов

### С транскрипцией (base model)
- ~30-60 секунд на 10-минутное видео
- ~1-2 GB RAM
- Рекомендуется GPU для ускорения

## Безопасность

- ✅ API ключи хранятся в переменных окружения
- ✅ Запуск от непривилегированного пользователя
- ✅ Валидация входных данных
- ✅ Ограничение размера загружаемых файлов

## Roadmap

- [ ] Поддержка YouTube плейлистов
- [ ] Извлечение субтитров вместо транскрипции
- [ ] Поддержка YouTube Shorts
- [ ] Webhook вместо polling (YouTube PubSubHubbub)
- [ ] Кэширование метаданных
- [ ] Поддержка приватных видео

## Лицензия

MIT

## Поддержка

При возникновении проблем создайте issue в репозитории проекта.
