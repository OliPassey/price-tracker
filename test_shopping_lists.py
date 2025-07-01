#!/usr/bin/env python3
"""
Test script for automated shopping list generation
"""

import os
import sys
sys.path.append(os.path.dirname(__file__))

from src.config import Config
from src.database import DatabaseManager
from src.notification import NotificationManager
from src.shopping_list import AutoShoppingListGenerator

def test_shopping_lists():
    """Test the automated shopping list generation."""
    print("🛒 Testing Automated Shopping List Generation")
    print("=" * 50)
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    notification_manager = NotificationManager(config)
    shopping_generator = AutoShoppingListGenerator(db_manager, notification_manager)
    
    # Generate shopping lists
    print("\n📊 Generating shopping lists...")
    shopping_lists = shopping_generator.generate_shopping_lists()
    summary = shopping_generator.get_summary_stats()
    
    # Display summary
    print(f"\n📈 Summary:")
    print(f"  • Total products: {summary['total_products']}")
    print(f"  • Total cost: £{summary['total_cost']:.2f}")
    print(f"  • Total savings: £{summary['total_savings']:.2f}")
    print(f"  • Stores involved: {summary['store_count']}")
    
    if summary['most_items_store']:
        print(f"  • Best store: {summary['most_items_store']} ({summary['most_items_count']} items)")
    
    # Display shopping lists
    print(f"\n🛍️ Shopping Lists by Store:")
    print("-" * 30)
    
    for store_list in shopping_lists:
        print(f"\n🏪 {store_list.store_display_name}")
        print(f"   Items: {store_list.item_count}")
        print(f"   Total: £{store_list.total_cost:.2f}")
        if store_list.total_savings > 0:
            print(f"   Savings: £{store_list.total_savings:.2f}")
        
        print(f"   Products:")
        for i, item in enumerate(store_list.items[:5], 1):
            savings_text = f" (save £{item.savings_vs_most_expensive:.2f})" if item.savings_vs_most_expensive > 0 else ""
            print(f"     {i}. {item.product_name}: £{item.current_price:.2f}{savings_text}")
        
        if len(store_list.items) > 5:
            print(f"     ... and {len(store_list.items) - 5} more items")
    
    if not shopping_lists:
        print("   No shopping lists available.")
        print("   Add some products and run a price scrape first.")
    
    print(f"\n✅ Shopping list generation complete!")
    
    # Test email sending (if configured)
    email_config = config.notification_config.get('email', {})
    if email_config.get('enabled') and email_config.get('recipient_email'):
        print(f"\n📧 Testing email notification...")
        try:
            success = shopping_generator.send_daily_shopping_list()
            if success:
                print(f"   ✅ Email sent successfully!")
            else:
                print(f"   ❌ Failed to send email (check configuration)")
        except Exception as e:
            print(f"   ❌ Error sending email: {str(e)}")
    else:
        print(f"\n📧 Email notifications not configured")
    
    return shopping_lists

if __name__ == "__main__":
    test_shopping_lists()
