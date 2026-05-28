FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/feedback-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared proto files
COPY shared /app/shared

# Copy service code
COPY services/feedback-service/ .

# Generate gRPC code from proto files
RUN python -m grpc_tools.protoc \
    -I/app/shared/proto \
    --python_out=/app/shared/proto \
    --grpc_python_out=/app/shared/proto \
    /app/shared/proto/feedback_service.proto

# Expose gRPC port
EXPOSE 50055

# Run the service
CMD ["python", "main.py"]
