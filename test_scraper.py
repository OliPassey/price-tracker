#!/usr/bin/env python3
"""
Test script to debug scraping issues for JJ Food Service and A to Z Catering
"""

import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.uk_scraper import UKCateringScraper
from src.config import Config
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_scraping():
    config = Config()
    
    async with UKCateringScraper(config) as scraper:
        # Test URLs that were problematic
        test_urls = [
            "https://www.jjfoodservice.com/catering-products/confectionery-and-snacks/chocolate/cadbury-dairy-milk-chocolate-bar-110g",
            "https://www.atozcatering.co.uk/catering-equipment/refrigeration/prep-fridges/polar-single-door-prep-counter-fridge-240ltr",
            "https://www.atozcatering.co.uk/catering-equipment/cooking-equipment/fryers/buffalo-single-tank-induction-fryer-5ltr"
        ]
        
        for url in test_urls:
            print(f"\n{'='*80}")
            print(f"Testing URL: {url}")
            print(f"{'='*80}")
            
            try:
                result = await scraper.scrape_product(url)
                if result:
                    print(f"Success! Result: {result}")
                else:
                    print("Failed to scrape product")
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scraping())
