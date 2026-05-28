# Интеллектуальная система фильтрации контента

Система генерации персонализированных дайджестов контента для снижения информационной нагрузки на основе микросервисной архитектуры с использованием NLP и брокера сообщений.

## 🎯 Цель проекта

Разработка интеллектуальной системы, которая:
- Собирает контент из различных источников (Telegram, VK, YouTube)
- Анализирует и суммаризирует публикации с помощью NLP
- Ранжирует контент по релевантности для каждого пользователя
- Генерирует персонализированные дайджесты
- Помогает пользователям осознанно потреблять информацию

## 🏗️ Архитектура

### Микросервисы

- **Bot Service** - Telegram бот для взаимодействия с пользователями
- **User Service** - Управление пользователями, профилями и подписками
- **Collector Services** - Сбор контента из различных платформ
  - Telegram Collector
  - VK Collector
  - YouTube Collector
- **Summarization Service** - Суммаризация текста с помощью NLP
- **Ranking Service** - Ранжирование контента и векторный поиск
- **Digest Service** - Генерация персонализированных дайджестов
- **Feedback Service** - Обработка обратной связи

### Технологический стек

- **Backend**: Python 3.11+
- **Database**: PostgreSQL + pgvector
- **Message Broker**: RabbitMQ
- **RPC**: gRPC + Protocol Buffers
- **NLP**: Transformers (Hugging Face), ruBERT, mBART
- **Containerization**: Docker + Docker Compose
- **Bot Framework**: aiogram 3.x

## 📋 Требования

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- 8 GB RAM (минимум), 16 GB (рекомендуется)
- 20 GB свободного места на диске

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd content-filter
```

### 2. Настройка окружения

```bash
# Создание .env файла
cp .env.example .env

# Редактирование .env с вашими настройками
nano .env
```

### 3. Запуск инфраструктуры

```bash
# Запуск PostgreSQL и RabbitMQ
docker-compose up -d postgres rabbitmq

# Проверка статуса
docker-compose ps
```

### 4. Проверка работоспособности

**PostgreSQL:**
```bash
docker exec -it content_filter_postgres psql -U postgres -d content_filter_db
```

**RabbitMQ Management UI:**
Откройте [http://localhost:15672](http://localhost:15672) (admin/admin_password)

## 📚 Документация

### Общая документация
- [**Руководство по настройке**](docs/SETUP.md) - Детальная инструкция по установке и конфигурации
- [**План реализации**](plans/implementation-plan.md) - Пошаговый план разработки
- [**Архитектура RabbitMQ**](docs/rabbitmq-architecture.md) - Описание очередей и обмена сообщениями

### Документация сервисов
- [**Bot Service**](services/bot-service/README.md) - Telegram бот
- [**User Service**](services/user-service/README.md) - Управление пользователями
- [**Telegram Collector**](services/collector-telegram/README.md) - Сбор контента из Telegram
- [**Summarization Service**](services/summarization-service/README.md) - Суммаризация и NLP-обработка

### Отчеты о завершении задач
- [**Task 3.2: Bot Service**](docs/TASK_3.2_COMPLETION.md) - ✅ Завершено
- [**Task 3.3: Telegram Collector**](docs/TASK_3.3_COMPLETION.md) - ✅ Завершено
- [**Task 3.4: Summarization Service**](docs/TASK_3.4_COMPLETION.md) - ✅ Завершено

### Быстрый старт
- [**Telegram Collector Quickstart**](docs/COLLECTOR_TELEGRAM_QUICKSTART.md) - Быстрый запуск коллектора

## 🗂️ Структура проекта

```
content-filter/
├── services/                    # Микросервисы
│   ├── bot-service/            # Telegram бот
│   ├── user-service/           # Управление пользователями
│   ├── collector-telegram/     # Коллектор Telegram
│   ├── collector-vk/           # Коллектор VK
│   ├── collector-youtube/      # Коллектор YouTube
│   ├── summarization-service/  # Суммаризация
│   ├── ranking-service/        # Ранжирование
│   └── digest-service/         # Генерация дайджестов
├── shared/                      # Общие компоненты
│   ├── proto/                  # gRPC контракты
│   ├── models/                 # Модели данных
│   └── generated/              # Сгенерированный gRPC код
├── infrastructure/              # Инфраструктура
│   ├── postgres/               # PostgreSQL конфигурация
│   │   ├── init.sql           # Инициализация
│   │   └── schema.sql         # Схема БД
│   └── rabbitmq/              # RabbitMQ конфигурация
│       ├── rabbitmq.conf
│       └── definitions.json
├── docs/                        # Документация
├── plans/                       # Планы разработки
├── tests/                       # Тесты
├── docker-compose.yml          # Docker Compose конфигурация
├── requirements.txt            # Python зависимости
└── README.md                   # Этот файл
```

## 🔧 Разработка

### Генерация gRPC кода

```bash
# Установка инструментов
pip install grpcio grpcio-tools

# Генерация Python кода
python -m grpc_tools.protoc \
    -I./shared/proto \
    --python_out=./shared/generated \
    --grpc_python_out=./shared/generated \
    ./shared/proto/*.proto
```

### Запуск тестов

```bash
# Установка зависимостей для тестирования
pip install pytest pytest-asyncio pytest-cov

# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=services --cov-report=html
```

### Линтинг и форматирование

```bash
# Установка инструментов
pip install black isort pylint

# Форматирование кода
black services/
isort services/

# Проверка качества кода
pylint services/
```

## 📊 Схема базы данных

Основные таблицы:
- `users` - Пользователи системы
- `user_profiles` - Профили и предпочтения
- `content_sources` - Источники контента
- `subscriptions` - Подписки пользователей
- `content_units` - Единицы контента
- `digests` - Сгенерированные дайджесты
- `digest_items` - Элементы дайджестов
- `feedback` - Обратная связь
- `quality_ratings` - Оценки качества потребления

Полная схема: [`infrastructure/postgres/schema.sql`](infrastructure/postgres/schema.sql)

## 🔄 Поток данных

```
1. Collector → RabbitMQ (raw content)
2. Summarization Service → Обработка и суммаризация
3. Ranking Service → Генерация эмбеддингов и ранжирование
4. Digest Service → Формирование дайджеста
5. Bot Service → Отправка пользователю
6. User → Обратная связь → Обновление профиля
```

## 🎯 Roadmap

### MVP (Release 1) - В разработке ⚙️
- [x] Инфраструктура (PostgreSQL, RabbitMQ)
- [x] Схема базы данных
- [x] gRPC контракты
- [x] Форматы сообщений RabbitMQ
- [x] User Service ✅
- [x] Bot Service (Telegram) ✅
- [x] Telegram Collector ✅
- [x] Summarization Service ✅
- [ ] Ranking Service 🔄
- [ ] Digest Service

### Release 2 - Планируется
- [ ] VK Collector
- [ ] YouTube Collector
- [ ] Импорт папок каналов Telegram
- [ ] Адаптивная детализация пересказа
- [ ] Настройка интервалов доставки

### Release 3 - Планируется
- [ ] Автоудаление старых дайджестов
- [ ] Прямая доставка видео
- [ ] Оценка качества потребления
- [ ] Визуализация прогресса (Цифровой сад)

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Пожалуйста:

1. Форкните репозиторий
2. Создайте ветку для вашей функции (`git checkout -b feature/AmazingFeature`)
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Запушьте в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📝 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для деталей.

## 📧 Контакты

- **Документация**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

## 🙏 Благодарности

- [Hugging Face](https://huggingface.co/) за NLP модели
- [pgvector](https://github.com/pgvector/pgvector) за векторный поиск в PostgreSQL
- [aiogram](https://github.com/aiogram/aiogram) за Telegram Bot framework

---

**Статус проекта**: 🚧 В активной разработке

**Текущий этап**: Этап 3 - Разработка MVP (Release 1) - 67% завершено

**Завершенные компоненты**:
- ✅ User Service (gRPC API для управления пользователями)
- ✅ Bot Service (Telegram бот с онбордингом и настройками)
- ✅ Telegram Collector (сбор контента из Telegram-каналов)
- ✅ Summarization Service (суммаризация текста и NLP-обработка)

**Следующие задачи**:
- 🔄 Ranking Service (задача 3.5) - ранжирование и векторные embeddings
- 📋 Digest Service (задача 3.6) - генерация персонализированных дайджестов

**Последнее обновление**: 2026-05-27
