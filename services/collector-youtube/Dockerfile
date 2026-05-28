# YouTube Collector Service Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# ffmpeg is required for audio extraction and whisper
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 collector && \
    mkdir -p /tmp/youtube_downloads && \
    chown -R collector:collector /app /tmp/youtube_downloads

USER collector

# Create temp directory for downloads
VOLUME /tmp/youtube_downloads

# Run the application
CMD ["python", "main.py"]
