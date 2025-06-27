#!/usr/bin/env python3
"""
Quick validation that the A to Z Catering pricing is working correctly
"""

import sys
import os
import asyncio

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def validate_atoz_pricing():
    """Test the A to Z Catering pricing fix."""
    
    try:
        from uk_scraper import UKCateringScraper
        from config import Config
        
        print("Testing A to Z Catering pricing fix...")
        print("=" * 50)
        
        config = Config()
        scraper = UKCateringScraper(config)
        
        # Test the problematic URL
        url = 'https://www.atoz-catering.co.uk/products/product/coca-cola-cans--coke-gb---24'
        
        print(f"Testing URL: {url}")
        print("Expected price: £12.99 (not £1.39)")
        print("Testing...")
        
        result = await scraper.scrape_product_price(url, 'atoz_catering')
        
        print(f"\nResults:")
        print(f"Success: {result['success']}")
        
        if result['success'] and result['price']:
            price = result['price']
            print(f"Price found: £{price}")
            
            if price == 12.99:
                print("✅ FIXED! Correct price detected (£12.99)")
            elif price == 1.39:
                print("❌ STILL BROKEN! Wrong price detected (£1.39)")
            else:
                print(f"⚠️  Different price detected: £{price}")
        else:
            print(f"❌ Failed to scrape: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(validate_atoz_pricing())
