# Интеллектуальная система фильтрации контента

Система генерации персонализированных дайджестов контента для снижения информационной нагрузки на основе микросервисной архитектуры с использованием NLP и брокера сообщений.

## Цель проекта

Разработка интеллектуальной системы, которая:
- Собирает контент из различных источников (Telegram, VK, YouTube)
- Анализирует и суммаризирует публикации с помощью NLP
- Ранжирует контент по релевантности для каждого пользователя
- Генерирует персонализированные дайджесты
- Помогает пользователям осознанно потреблять информацию

### Технологический стек

- **Backend**: Python 3.11+
- **Database**: PostgreSQL + pgvector
- **Message Broker**: RabbitMQ
- **RPC**: gRPC + Protocol Buffers
- **NLP**: Transformers (Hugging Face), ruBERT, mBART
- **Containerization**: Docker + Docker Compose
- **Bot Framework**: aiogram 3.x
- 
## Структура проекта

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
├── docker-compose.yml          # Docker Compose конфигурация
├── requirements.txt            # Python зависимости
└── README.md                   # Этот файл
```

