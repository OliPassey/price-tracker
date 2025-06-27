#!/uhttps://www.atoz-catering.co.uksr/bin/env python3
"""
Price Tracker - Web Scraper for Product Price Monitoring
Tracks product prices across multiple e-commerce sites
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
import argparse

from src.scraper_manager import ScraperManager
from src.database import DatabaseManager
from src.config import Config
from src.notification import NotificationManager
from src.web_ui import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_tracker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_scraper():
    """Run the price scraping process."""
    try:
        config = Config()
        db_manager = DatabaseManager(config.database_path)
        scraper_manager = ScraperManager(config)
        notification_manager = NotificationManager(config)
        
        logger.info("Starting price tracking session")
        
        # Load products from database
        products = db_manager.get_all_products()
        if not products:
            logger.warning("No products found in database. Add products first.")
            return
        
        # Scrape prices for all products
        results = await scraper_manager.scrape_all_products(products)
        
        # Process results and save to database
        price_alerts = []
        for product_id, site_prices in results.items():
            for site_name, price_data in site_prices.items():
                if price_data['success']:
                    # Save price to database
                    db_manager.save_price_history(
                        product_id=product_id,
                        site_name=site_name,
                        price=price_data['price'],
                        currency=price_data.get('currency', 'USD'),
                        availability=price_data.get('availability', True),
                        timestamp=datetime.now()
                    )
                    
                    # Check for price alerts
                    product = db_manager.get_product(product_id)
                    if product and price_data['price'] <= product['target_price']:
                        price_alerts.append({
                            'product': product,
                            'site': site_name,
                            'current_price': price_data['price'],
                            'target_price': product['target_price']
                        })
        
        # Send notifications for price alerts
        if price_alerts:
            await notification_manager.send_price_alerts(price_alerts)
        
        logger.info(f"Scraping completed. Found {len(price_alerts)} price alerts.")
        
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise


def run_web_ui():
    """Run the web UI for managing products and viewing price history."""
    import os
    
    # Use environment variables for configuration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production').lower() != 'production'
    
    app = create_app()
    logger.info(f"Starting Price Tracker web server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)


def main():
    parser = argparse.ArgumentParser(description='Price Tracker')
    parser.add_argument('--mode', choices=['scrape', 'web'], default='web',
                       help='Run mode: scrape prices or start web UI')
    parser.add_argument('--config', help='Path to config file')
    
    args = parser.parse_args()
    
    if args.mode == 'scrape':
        asyncio.run(run_scraper())
    else:
        run_web_ui()


if __name__ == "__main__":
    main()
