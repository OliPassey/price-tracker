"""
Example script to add UK catering sample products for testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import DatabaseManager
from src.config import Config

def add_uk_catering_products():
    """Add some sample UK catering products for testing."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    
    # Sample UK catering products with example URLs
    # Note: These are example URLs - you'll need to replace with real product URLs
    sample_products = [
        {
            'name': 'McCain Straight Cut Oven Chips 2.5kg',
            'description': 'Frozen straight cut oven chips for catering use',
            'target_price': 4.50,
            'urls': {
                'jjfoodservice': 'https://www.jjfoodservice.com/products/mccain-straight-cut-oven-chips',
                'atoz_catering': 'https://www.atoz-catering.co.uk/products/product/mccain-straight-cut-oven-chips-25kg'
            }
        },
        {
            'name': 'Heinz Baked Beans 6x2.62kg',
            'description': 'Catering size baked beans in tomato sauce',
            'target_price': 25.00,
            'urls': {
                'atoz_catering': 'https://www.atoz-catering.co.uk/products/product/heinz-baked-beans--6x262kg',
                'jjfoodservice': 'https://www.jjfoodservice.com/products/heinz-baked-beans-catering'
            }
        },
        {
            'name': 'Chef Select Chicken Breast Fillets 2kg',
            'description': 'Fresh chicken breast fillets for professional kitchens',
            'target_price': 12.00,
            'urls': {
                'jjfoodservice': 'https://www.jjfoodservice.com/products/chicken-breast-fillets-2kg',
                'atoz_catering': 'https://www.atoz-catering.co.uk/products/product/chicken-breast-fillets-2kg'
            }
        },
        {
            'name': 'Whole Milk 2 Litre Bottles (Case of 6)',
            'description': 'Fresh whole milk in 2L bottles for catering',
            'target_price': 8.00,
            'urls': {
                'atoz_catering': 'https://www.atoz-catering.co.uk/products/product/cotteswold-whole-milk-1x2lt-blue',
                'jjfoodservice': 'https://www.jjfoodservice.com/products/whole-milk-2l-case'
            }
        },
        {
            'name': 'Vegetable Oil 20L Container',
            'description': 'Catering vegetable oil for deep frying and cooking',
            'target_price': 35.00,
            'urls': {
                'jjfoodservice': 'https://www.jjfoodservice.com/products/vegetable-oil-20l',
                'atoz_catering': 'https://www.atoz-catering.co.uk/products/product/vegetable-oil-20l-container'
            }
        },
        {
            'name': 'Plain Flour 16kg Sack',
            'description': 'Professional baking flour for commercial use',
            'target_price': 18.00,
            'urls': {
                'atoz_catering': 'https://www.atoz-catering.co.uk/products/product/plain-flour-16kg-sack',
                'jjfoodservice': 'https://www.jjfoodservice.com/products/plain-flour-16kg'
            }
        }
    ]
    
    print("Adding UK catering sample products...")
    
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
    
    print("\nUK catering sample products added successfully!")
    print("Note: The URLs in this example are placeholders.")
    print("You'll need to replace them with real product URLs from:")
    print("- JJ Food Service: https://www.jjfoodservice.com/")
    print("- A to Z Catering: https://www.atoz-catering.co.uk/")
    print("\nYou can now run the web UI with: python main.py --mode web")
    print("Or start scraping with: python main.py --mode scrape")

if __name__ == "__main__":
    add_uk_catering_products()
