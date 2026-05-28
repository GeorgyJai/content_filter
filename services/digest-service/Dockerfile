# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY services/digest-service/requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем shared proto файлы
COPY shared/proto /app/shared/proto

# Генерируем Python код из proto файлов
RUN python -m grpc_tools.protoc \
    -I/app/shared/proto \
    --python_out=/app/shared/proto \
    --grpc_python_out=/app/shared/proto \
    /app/shared/proto/digest_service.proto \
    /app/shared/proto/ranking_service.proto \
    /app/shared/proto/user_service.proto

# Создаем __init__.py для shared.proto
RUN touch /app/shared/__init__.py && touch /app/shared/proto/__init__.py

# Копируем код сервиса
COPY services/digest-service/ /app/

# Создаем директорию для логов
RUN mkdir -p /app/logs

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50052'); channel.close()" || exit 1

# Запускаем сервис
CMD ["python", "main.py"]
