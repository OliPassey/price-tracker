#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from uk_scraper import scrape_jj_foodservice

async def test_actual_scraper():
    url = "https://www.jjfoodservice.com/product/London-Enfield/BAC002/"
    
    print(f"Testing actual scraper with URL: {url}")
    print("=" * 60)
    
    try:
        result = await scrape_jj_foodservice(url)
        print(f"Scraper result: {result}")
        
        if result:
            print(f"✅ Name: {result.get('name', 'Not found')}")
            print(f"✅ Collection Price: £{result.get('collection_price', 'Not found')}")
            print(f"✅ Delivery Price: £{result.get('delivery_price', 'Not found')}")
            print(f"✅ Image URL: {result.get('image_url', 'Not found')}")
        else:
            print("❌ Scraper returned None")
            
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_actual_scraper())
