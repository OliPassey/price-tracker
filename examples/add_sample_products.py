"""
Example script to add sample products for testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import DatabaseManager
from src.config import Config

def add_sample_products():
    """Add some sample products for testing."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    
    # Sample products with real URLs (for demonstration)
    sample_products = [
        {
            'name': 'AirPods Pro (2nd Generation)',
            'description': 'Apple AirPods Pro with Active Noise Cancellation',
            'target_price': 200.00,
            'urls': {
                'amazon': 'https://www.amazon.com/dp/B0BDHWDR12',
                'walmart': 'https://www.walmart.com/ip/AirPods-Pro-2nd-generation/1952646965'
            }
        },
        {
            'name': 'Sony WH-1000XM4 Headphones',
            'description': 'Wireless Noise Canceling Over-Ear Headphones',
            'target_price': 250.00,
            'urls': {
                'amazon': 'https://www.amazon.com/dp/B0863TXGM3',
                'ebay': 'https://www.ebay.com/itm/Sony-WH-1000XM4-Wireless-Headphones/324298765234'
            }
        },
        {
            'name': 'iPad Air (5th Generation)',
            'description': '10.9-inch iPad Air with M1 Chip, 64GB',
            'target_price': 500.00,
            'urls': {
                'amazon': 'https://www.amazon.com/dp/B09V3HN1KC',
                'walmart': 'https://www.walmart.com/ip/iPad-Air-5th-Gen/612825603'
            }
        },
        {
            'name': 'Nintendo Switch OLED',
            'description': 'Nintendo Switch OLED Model Gaming Console',
            'target_price': 300.00,
            'urls': {
                'amazon': 'https://www.amazon.com/dp/B098RKWHHZ',
                'walmart': 'https://www.walmart.com/ip/Nintendo-Switch-OLED/910582148'
            }
        },
        {
            'name': 'Samsung 55" 4K Smart TV',
            'description': 'Samsung 55-inch Crystal UHD 4K Smart TV',
            'target_price': 400.00,
            'urls': {
                'amazon': 'https://www.amazon.com/dp/B08T6F5H1Y',
                'walmart': 'https://www.walmart.com/ip/Samsung-55-Class-4K-Crystal-UHD/485926403'
            }
        }
    ]
    
    print("Adding sample products...")
    
    for product_data in sample_products:
        try:
            product_id = db_manager.add_product(
                name=product_data['name'],
                description=product_data['description'],
                target_price=product_data['target_price'],
                urls=product_data['urls']
            )
            print(f"✓ Added: {product_data['name']} (ID: {product_id})")
        except Exception as e:
            print(f"✗ Failed to add {product_data['name']}: {e}")
    
    print("\nSample products added successfully!")
    print("You can now run the web UI with: python main.py --mode web")
    print("Or start scraping with: python main.py --mode scrape")

if __name__ == "__main__":
    add_sample_products()
