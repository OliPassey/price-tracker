#!/usr/bin/env python3
"""
Debug script to test JJ Food Service scraping
"""

import asyncio
import logging
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.config import Config
from src.uk_scraper import UKCateringScraper

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_jj_scraping():
    config = Config()
    
    print(f"JJ Food Service enabled: {config.is_site_enabled('jjfoodservice')}")
    print(f"A to Z enabled: {config.is_site_enabled('atoz_catering')}")
    
    url = "https://www.jjfoodservice.com/product/London-Enfield/BAC002/"
    
    async with UKCateringScraper(config) as scraper:
        print(f"\nTesting JJ Food Service URL: {url}")
        result = await scraper.scrape_product_price(url, 'jjfoodservice')
        print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_jj_scraping())
