# Use Python 3.11 slim image (revert from 3.12)
FROM python:3.11-slim

# Install cron and other dependencies
RUN apt-get update && apt-get install -y \
    cron \
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
    RETRY_ATTEMPTS=3

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

# Create the daily scraper script
RUN echo '#!/usr/bin/env python3\n\
import sys\n\
import os\n\
import asyncio\n\
import logging\n\
from datetime import datetime\n\
\n\
# Configure logging\n\
logging.basicConfig(\n\
    level=logging.INFO,\n\
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",\n\
    handlers=[\n\
        logging.FileHandler("/var/log/price_scraper.log"),\n\
        logging.StreamHandler()\n\
    ]\n\
)\n\
\n\
logger = logging.getLogger(__name__)\n\
\n\
async def main():\n\
    try:\n\
        from src.config import Config\n\
        from src.database import DatabaseManager\n\
        from src.scraper_manager import ScraperManager\n\
        \n\
        logger.info("Starting scheduled price scraping")\n\
        \n\
        config = Config()\n\
        if config.has_config_error():\n\
            logger.error(f"Configuration error: {config.get_config_error()}")\n\
            return\n\
        \n\
        db_manager = DatabaseManager(config.database_path)\n\
        scraper_manager = ScraperManager(config)\n\
        \n\
        products = db_manager.get_all_products()\n\
        if not products:\n\
            logger.warning("No products found to scrape")\n\
            return\n\
        \n\
        logger.info(f"Scraping {len(products)} products")\n\
        results = await scraper_manager.scrape_all_products(products)\n\
        \n\
        total = sum(len(sites) for sites in results.values())\n\
        successful = sum(1 for sites in results.values() for result in sites.values() if result["success"])\n\
        \n\
        logger.info(f"Scraping complete: {successful}/{total} successful")\n\
        \n\
        # Save results to database\n\
        for product_id, site_results in results.items():\n\
            for site_name, result in site_results.items():\n\
                if result["success"]:\n\
                    db_manager.save_price_history(\n\
                        product_id=product_id,\n\
                        site_name=site_name,\n\
                        price=result["price"],\n\
                        availability=result.get("availability", True),\n\
                        timestamp=datetime.now()\n\
                    )\n\
                    \n\
    except Exception as e:\n\
        logger.error(f"Scheduled scraping failed: {str(e)}", exc_info=True)\n\
\n\
if __name__ == "__main__":\n\
    asyncio.run(main())\n\
' > /app/daily_scraper.py && chmod +x /app/daily_scraper.py

# Create cron job - runs daily at 8 AM
RUN echo "0 15 * * * cd /app && python daily_scraper.py >> /var/log/cron.log 2>&1" > /etc/cron.d/price-tracker
RUN chmod 0644 /etc/cron.d/price-tracker
RUN crontab /etc/cron.d/price-tracker

# Create startup script that ensures directories exist and have correct permissions
RUN echo '#!/bin/bash\n\
# Ensure data directory exists and has correct permissions\n\
mkdir -p /app/data /var/log\n\
chown -R tracker:tracker /app/data /var/log\n\
chmod 755 /app/data /var/log\n\
\n\
# Start cron in background\n\
cron\n\
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
