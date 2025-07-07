# Use Python 3.11 slim image (revert from 3.12)
FROM python:3.11-slim

# Install system dependencies (remove cron)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=main.py \
    FLASK_ENV=production

# Optional: Set default configuration via environment variables
ENV DATABASE_PATH=/app/data/price_tracker.db \
    DELAY_BETWEEN_REQUESTS=2 \
    MAX_CONCURRENT_REQUESTS=1 \
    REQUEST_TIMEOUT=30 \
    RETRY_ATTEMPTS=3 \
    WEBHOOK_SECRET=your-secret-key-here

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tracker

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /var/log && \
    chmod 755 /app/data /var/log && \
    chown -R tracker:tracker /app/data /var/log

# Copy application code
COPY . .

# Create startup script without cron
RUN echo '#!/bin/bash\n\
# Ensure data directory exists and has correct permissions\n\
mkdir -p /app/data /var/log\n\
chown -R tracker:tracker /app/data /var/log\n\
chmod 755 /app/data /var/log\n\
\n\
# Switch to non-root user and start web server\n\
exec su tracker -c "python main.py --mode web"\n\
' > /app/start.sh && chmod +x /app/start.sh

# Set ownership for application files
RUN chown -R tracker:tracker /app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run startup script
CMD ["/app/start.sh"]
