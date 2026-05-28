FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/user-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/user-service/ .

# Copy shared proto files
COPY shared/proto /app/shared/proto

# Generate gRPC code from proto files
RUN python -m grpc_tools.protoc \
    -I/app/shared/proto \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/shared/proto/user_service.proto

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); channel.close()" || exit 1

# Run the service
CMD ["python", "main.py"]
