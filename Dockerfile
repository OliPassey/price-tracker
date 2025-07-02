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
        from src.notification import NotificationManager\n\
        from src.shopping_list import AutoShoppingListGenerator\n\
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
        notification_manager = NotificationManager(config)\n\
        shopping_list_generator = AutoShoppingListGenerator(db_manager)\n\
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
        failed = total - successful\n\
        \n\
        logger.info(f"Scraping complete: {successful}/{total} successful")\n\
        \n\
        # Save results and collect price alerts\n\
        price_alerts = []\n\
        for product_id, site_results in results.items():\n\
            product = db_manager.get_product(product_id)\n\
            for site_name, result in site_results.items():\n\
                if result["success"]:\n\
                    # Save to database\n\
                    db_manager.save_price_history(\n\
                        product_id=product_id,\n\
                        site_name=site_name,\n\
                        price=result["price"],\n\
                        availability=result.get("availability", True),\n\
                        timestamp=datetime.now()\n\
                    )\n\
                    \n\
                    # Check for price alerts\n\
                    if product and product.get("target_price") and result["price"] <= product["target_price"]:\n\
                        price_alerts.append({\n\
                            "product": product,\n\
                            "site": site_name,\n\
                            "current_price": result["price"],\n\
                            "target_price": product["target_price"],\n\
                            "url": result.get("url", "")\n\
                        })\n\
        \n\
        # Send price alerts if any\n\
        if price_alerts:\n\
            alert_message = "Price Alerts:\\n\\n"\n\
            for alert in price_alerts:\n\
                alert_message += f"🎯 {alert[\"product\"][\"name\"]}\\n"\n\
                alert_message += f"   Store: {alert[\"site\"]}\\n"\n\
                alert_message += f"   Price: £{alert[\"current_price\"]} (Target: £{alert[\"target_price\"]})\\n"\n\
                alert_message += f"   URL: {alert[\"url\"]}\\n\\n"\n\
            \n\
            await notification_manager.send_notification(\n\
                subject=f"Price Alert: {len(price_alerts)} item(s) on sale!",\n\
                message=alert_message\n\
            )\n\
            logger.info(f"Sent price alerts for {len(price_alerts)} items")\n\
        \n\
        # Generate and send daily shopping list\n\
        try:\n\
            shopping_lists = shopping_list_generator.generate_all_shopping_lists()\n\
            if shopping_lists:\n\
                shopping_message = "Daily Shopping List (Best Prices):\\n\\n"\n\
                total_savings = 0\n\
                \n\
                for store_name, store_list in shopping_lists.items():\n\
                    if store_list.items:\n\
                        shopping_message += f"🏪 {store_name.upper()}:\\n"\n\
                        store_total = 0\n\
                        for item in store_list.items:\n\
                            shopping_message += f"   • {item.product_name} - £{item.current_price}\\n"\n\
                            store_total += item.current_price\n\
                            if item.savings_amount > 0:\n\
                                total_savings += item.savings_amount\n\
                        shopping_message += f"   Subtotal: £{store_total:.2f}\\n\\n"\n\
                \n\
                if total_savings > 0:\n\
                    shopping_message += f"💰 Total Savings: £{total_savings:.2f}\\n"\n\
                \n\
                await notification_manager.send_notification(\n\
                    subject="Daily Shopping List - Best Prices",\n\
                    message=shopping_message\n\
                )\n\
                logger.info("Sent daily shopping list")\n\
        except Exception as e:\n\
            logger.error(f"Failed to generate shopping list: {e}")\n\
        \n\
        # Send scraping summary\n\
        summary_message = f"Daily Price Scraping Summary:\\n\\n"\n\
        summary_message += f"📊 Products scraped: {len(products)}\\n"\n\
        summary_message += f"✅ Successful: {successful}\\n"\n\
        summary_message += f"❌ Failed: {failed}\\n"\n\
        summary_message += f"🎯 Price alerts: {len(price_alerts)}\\n"\n\
        summary_message += f"🕐 Completed at: {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\\n"\n\
        \n\
        await notification_manager.send_notification(\n\
            subject="Daily Price Scraping Complete",\n\
            message=summary_message\n\
        )\n\
        logger.info("Sent scraping summary")\n\
                    \n\
    except Exception as e:\n\
        logger.error(f"Scheduled scraping failed: {str(e)}", exc_info=True)\n\
        \n\
        # Send error notification\n\
        try:\n\
            from src.config import Config\n\
            from src.notification import NotificationManager\n\
            config = Config()\n\
            notification_manager = NotificationManager(config)\n\
            await notification_manager.send_notification(\n\
                subject="Price Scraping Failed",\n\
                message=f"Daily price scraping failed with error:\\n\\n{str(e)}"\n\
            )\n\
        except:\n\
            pass  # If notification also fails, just log\n\
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
