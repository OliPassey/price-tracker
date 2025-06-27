#!/usr/bin/env python3
"""
Special Pricing Debug Tool for UK Price Tracker

This tool helps debug and monitor special pricing detection on real websites.
It can be used to test URLs and see exactly what pricing information is being detected.
"""

import sys
import os
import asyncio
import logging
import argparse
from typing import Dict, Any

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from uk_scraper import UKCateringScraper
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def detect_site_from_url(url: str) -> str:
    """Detect which site the URL belongs to."""
    if 'jjfoodservice.com' in url:
        return 'jjfoodservice'
    elif 'atoz-catering.co.uk' in url:
        return 'atoz_catering'
    elif 'amazon.co.uk' in url:
        return 'amazon_uk'
    else:
        return 'unknown'


async def debug_url_pricing(url: str, verbose: bool = False):
    """Debug pricing extraction for a specific URL."""
    
    config = Config()
    scraper = UKCateringScraper(config)
    
    site_name = detect_site_from_url(url)
    
    print(f"Debugging URL: {url}")
    print(f"Detected site: {site_name}")
    print("-" * 60)
    
    if site_name == 'unknown':
        print("❌ Unknown site - cannot process")
        return
    
    try:
        # Fetch the page content
        print("🌐 Fetching page content...")
        html_content = await scraper._fetch_page(url)
        
        if not html_content:
            print("❌ Failed to fetch page content")
            return
        
        print("✅ Page content fetched successfully")
        
        # Parse with BeautifulSoup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Debug special pricing detection
        print("\n🔍 Looking for special offer prices...")
        special_prices = scraper._find_special_offer_prices(soup, site_name)
        
        if special_prices:
            print(f"✅ Found {len(special_prices)} special offer prices:")
            for price, selector in special_prices:
                print(f"   £{price} (found with: {selector})")
            
            best_special_price = min(price for price, _ in special_prices)
            print(f"🎯 Best special offer price: £{best_special_price}")
        else:
            print("❌ No special offer prices found")
        
        # Test the main extraction method
        print(f"\n🔍 Testing {site_name} extraction method...")
        
        if site_name == 'jjfoodservice':
            result = scraper._extract_jjfoodservice_data(soup)
        elif site_name == 'atoz_catering':
            result = scraper._extract_atoz_catering_data(soup)
        elif site_name == 'amazon_uk':
            result = scraper._extract_amazon_uk_data(soup)
        
        print(f"✅ Extraction result:")
        print(f"   Price: £{result['price']}" if result['price'] else "   Price: Not found")
        print(f"   Title: {result.get('title', 'Not found')}")
        print(f"   Available: {result.get('availability', 'Unknown')}")
        print(f"   Currency: {result.get('currency', 'Unknown')}")
        
        # If verbose, show more debugging info
        if verbose:
            print(f"\n🔍 Verbose debugging for {site_name}...")
            
            # Get site selectors from config
            site_config = config.get_site_config(site_name)
            if site_config and 'selectors' in site_config:
                selectors = site_config['selectors']
                
                # Test each selector type
                for selector_type, selector_list in selectors.items():
                    print(f"\n  Testing {selector_type} selectors:")
                    
                    for selector in selector_list:
                        try:
                            elements = soup.select(selector)
                            if elements:
                                print(f"    ✅ {selector} -> Found {len(elements)} elements")
                                for i, elem in enumerate(elements[:3]):  # Show first 3
                                    text = elem.get_text(strip=True)[:100]  # Truncate long text
                                    print(f"       [{i+1}] {text}")
                            else:
                                print(f"    ❌ {selector} -> No elements found")
                        except Exception as e:
                            print(f"    ⚠️  {selector} -> Error: {e}")
        
        # Test the full scraping method
        print(f"\n🔍 Testing full scrape_product_price method...")
        full_result = await scraper.scrape_product_price(url, site_name)
        
        print("✅ Full scraping result:")
        print(f"   Success: {full_result['success']}")
        print(f"   Price: £{full_result['price']}" if full_result['price'] else "   Price: Not found")
        print(f"   Error: {full_result.get('error', 'None')}")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        if verbose:
            import traceback
            traceback.print_exc()


def main():
    """Main function to run the debug tool."""
    
    parser = argparse.ArgumentParser(description='Debug special pricing detection for UK price tracker')
    parser.add_argument('url', help='URL to debug')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--test-selectors', action='store_true', help='Test all selectors from config')
    
    args = parser.parse_args()
    
    print("UK Price Tracker - Special Pricing Debug Tool")
    print("=" * 60)
    
    # Run the debugging
    asyncio.run(debug_url_pricing(args.url, args.verbose))


if __name__ == "__main__":
    main()
