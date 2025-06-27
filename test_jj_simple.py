#!/usr/bin/env python3
"""
Simple test to debug JJ Food Service scraping
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.uk_scraper import UKCateringScraper
from src.config import Config
import logging

# Set up verbose logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

async def test_jj_scraping():
    config = Config()
    
    async with UKCateringScraper(config) as scraper:
        url = "https://www.jjfoodservice.com/product/London-Enfield/BAC002/"
        
        print(f"Testing URL: {url}")
        
        # Get the raw HTML content
        html_content = await scraper._fetch_page(url)
        
        if html_content:
            print(f"HTML content length: {len(html_content)}")
            print("First 500 characters of HTML:")
            print(html_content[:500])
            print("\n" + "="*50 + "\n")
            
            # Look for delivery text
            if 'DELIVERY' in html_content:
                print("Found 'DELIVERY' in HTML content")
                # Find the context around DELIVERY
                delivery_pos = html_content.find('DELIVERY')
                context = html_content[delivery_pos:delivery_pos+100]
                print(f"Context around DELIVERY: {context}")
            else:
                print("'DELIVERY' not found in HTML content")
            
            # Look for any price patterns
            import re
            price_matches = re.findall(r'£(\d{1,3}(?:\.\d{2})?)', html_content)
            print(f"All price patterns found: {price_matches}")
            
        else:
            print("Failed to fetch HTML content")

if __name__ == "__main__":
    asyncio.run(test_jj_scraping())
