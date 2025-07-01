#!/usr/bin/env python3
"""
Daily shopping list scheduler for price tracker
Run this script daily (e.g., via cron) to automatically generate and send shopping lists.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, time

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.config import Config
from src.database import DatabaseManager
from src.notification import NotificationManager
from src.shopping_list import ShoppingListManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('shopping_list_scheduler.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main scheduler function."""
    logger.info("Starting shopping list scheduler")
    
    try:
        # Initialize components
        config = Config()
        
        if config.has_config_error():
            logger.error(f"Configuration error: {config.get_config_error()}")
            return
        
        db_manager = DatabaseManager(config.database_path)
        notification_manager = NotificationManager(config)
        shopping_list_manager = ShoppingListManager(db_manager, notification_manager)
        
        # Generate shopping lists for all enabled stores
        logger.info("Generating shopping lists for all enabled stores")
        shopping_lists = shopping_list_manager.generate_all_shopping_lists()
        
        if not shopping_lists:
            logger.warning("No shopping lists generated - no enabled stores or no products")
            return
        
        logger.info(f"Generated {len(shopping_lists)} shopping lists")
        
        # Check which stores should send at this time
        current_time = datetime.now().time()
        lists_to_send = {}
        
        for store_name, shopping_list in shopping_lists.items():
            preferences = shopping_list_manager.get_store_preferences(store_name)
            
            # Parse send time
            send_time_str = preferences.get('send_time', '09:00')
            try:
                send_time = time.fromisoformat(send_time_str)
                # Allow a 30-minute window around the scheduled time
                time_diff = abs((current_time.hour * 60 + current_time.minute) - 
                              (send_time.hour * 60 + send_time.minute))
                
                if time_diff <= 30:  # Within 30 minutes
                    lists_to_send[store_name] = shopping_list
                    logger.info(f"Scheduling {store_name} for sending (scheduled: {send_time_str}, current: {current_time.strftime('%H:%M')})")
                else:
                    logger.info(f"Skipping {store_name} - not scheduled time (scheduled: {send_time_str}, current: {current_time.strftime('%H:%M')})")
                    
            except ValueError:
                logger.warning(f"Invalid send time format for {store_name}: {send_time_str}")
                # Default to sending if time format is invalid
                lists_to_send[store_name] = shopping_list
        
        if not lists_to_send:
            logger.info("No shopping lists scheduled for this time")
            return
        
        # Send the scheduled shopping lists
        logger.info(f"Sending {len(lists_to_send)} shopping lists")
        results = await shopping_list_manager.send_shopping_lists(lists_to_send)
        
        # Log results
        successful = 0
        for store_name, success in results.items():
            if success:
                successful += 1
                logger.info(f"Successfully sent shopping list for {store_name}")
            else:
                logger.error(f"Failed to send shopping list for {store_name}")
        
        logger.info(f"Shopping list scheduler completed: {successful}/{len(results)} sent successfully")
        
    except Exception as e:
        logger.error(f"Shopping list scheduler failed: {str(e)}", exc_info=True)
        raise


def force_send_all():
    """Force send all shopping lists regardless of schedule."""
    logger.info("Force sending all shopping lists")
    
    async def force_send():
        config = Config()
        
        if config.has_config_error():
            logger.error(f"Configuration error: {config.get_config_error()}")
            return
        
        db_manager = DatabaseManager(config.database_path)
        notification_manager = NotificationManager(config)
        shopping_list_manager = ShoppingListManager(db_manager, notification_manager)
        
        shopping_lists = shopping_list_manager.generate_all_shopping_lists()
        
        if shopping_lists:
            results = await shopping_list_manager.send_shopping_lists(shopping_lists)
            successful = sum(1 for success in results.values() if success)
            logger.info(f"Force send completed: {successful}/{len(results)} sent successfully")
        else:
            logger.warning("No shopping lists to send")
    
    asyncio.run(force_send())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Daily shopping list scheduler")
    parser.add_argument('--force', action='store_true', 
                       help='Force send all shopping lists regardless of schedule')
    parser.add_argument('--dry-run', action='store_true',
                       help='Generate lists but do not send them')
    
    args = parser.parse_args()
    
    if args.force:
        force_send_all()
    elif args.dry_run:
        logger.info("Dry run mode - generating lists without sending")
        
        config = Config()
        if config.has_config_error():
            logger.error(f"Configuration error: {config.get_config_error()}")
            sys.exit(1)
        
        db_manager = DatabaseManager(config.database_path)
        notification_manager = NotificationManager(config)
        shopping_list_manager = ShoppingListManager(db_manager, notification_manager)
        
        shopping_lists = shopping_list_manager.generate_all_shopping_lists()
        
        for store_name, shopping_list in shopping_lists.items():
            logger.info(f"{store_name}: {shopping_list.item_count} items, "
                       f"£{shopping_list.total_cost:.2f} total, "
                       f"£{shopping_list.total_savings:.2f} savings")
    else:
        asyncio.run(main())
