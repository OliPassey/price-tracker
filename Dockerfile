# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=main.py \
    FLASK_ENV=production

# Optional: Set default configuration via environment variables
# These can be overridden when running the container
ENV DATABASE_PATH=/app/data/price_tracker.db \
    DELAY_BETWEEN_REQUESTS=2 \
    MAX_CONCURRENT_REQUESTS=1 \
    REQUEST_TIMEOUT=30 \
    RETRY_ATTEMPTS=3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tracker && \
    chown -R tracker:tracker /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs && \
    mkdir -p /app/data && \
    chown -R tracker:tracker /app

# Switch to non-root user
USER tracker

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["python", "main.py"]
