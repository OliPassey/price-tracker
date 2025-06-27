"""
Scheduled price scraping script for cron jobs
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.database import DatabaseManager
from src.scraper_manager import ScraperManager
from src.notification import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduled_scraping.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def run_scheduled_scraping():
    """Run the scheduled price scraping."""
    try:
        logger.info("=== Starting scheduled price scraping ===")
        
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config.database_path)
        scraper_manager = ScraperManager(config)
        notification_manager = NotificationManager(config)
        
        # Get all products
        products = db_manager.get_all_products()
        if not products:
            logger.warning("No products found in database")
            return
        
        logger.info(f"Found {len(products)} products to scrape")
        
        # Scrape all products
        results = await scraper_manager.scrape_all_products(products)
        
        # Process results
        total_success = 0
        total_failed = 0
        price_alerts = []
        
        for product_id, site_results in results.items():
            product = db_manager.get_product(product_id)
            
            for site_name, result in site_results.items():
                if result['success']:
                    total_success += 1
                    
                    # Save to database
                    db_manager.save_price_history(
                        product_id=product_id,
                        site_name=site_name,
                        price=result['price'],
                        currency=result.get('currency', 'USD'),
                        availability=result.get('availability', True),
                        timestamp=datetime.now()
                    )
                    
                    # Check for price alerts
                    if product and product['target_price'] and result['price'] <= product['target_price']:
                        price_alerts.append({
                            'product': product,
                            'site': site_name,
                            'current_price': result['price'],
                            'target_price': product['target_price']
                        })
                        
                        logger.info(f"Price alert: {product['name']} on {site_name} - ${result['price']:.2f}")
                else:
                    total_failed += 1
                    logger.error(f"Failed to scrape {product['name']} on {site_name}: {result.get('error', 'Unknown error')}")
        
        # Send notifications for price alerts
        if price_alerts:
            await notification_manager.send_price_alerts(price_alerts)
            logger.info(f"Sent notifications for {len(price_alerts)} price alerts")
        
        logger.info(f"Scraping completed: {total_success} successful, {total_failed} failed")
        logger.info(f"Found {len(price_alerts)} price alerts")
        
    except Exception as e:
        logger.error(f"Error during scheduled scraping: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(run_scheduled_scraping())
