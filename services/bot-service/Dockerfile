# Bot Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/bot-service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/bot-service/ .

# Copy shared proto files
COPY shared/proto /app/proto

# Generate gRPC code from proto files
RUN python -m grpc_tools.protoc \
    -I/app/proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/proto/user_service.proto

# Set Python path to include shared proto directory
ENV PYTHONPATH="${PYTHONPATH}:/app:/app/proto"

# Run the bot
CMD ["python", "main.py"]
