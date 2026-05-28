# Используем официальный Python образ
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование requirements.txt
COPY services/ranking-service/requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование proto файлов и генерация gRPC кода
COPY shared/proto /app/shared/proto
WORKDIR /app/shared/proto
RUN python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    ranking_service.proto

# Возврат в рабочую директорию
WORKDIR /app

# Копирование кода сервиса
COPY services/ranking-service/ .

# Создание директории для кэша моделей
RUN mkdir -p /app/model_cache
ENV TRANSFORMERS_CACHE=/app/model_cache

# Открытие порта для gRPC
EXPOSE 50053

# Запуск сервиса
CMD ["python", "main.py"]
