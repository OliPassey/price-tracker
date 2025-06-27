#!/usr/bin/env python3
"""
Test script for special pricing detection in UK scraper.
This script tests various special pricing scenarios to ensure the enhanced detection works correctly.
"""

import sys
import os
import asyncio
import logging
from bs4 import BeautifulSoup

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from uk_scraper import UKCateringScraper
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_test_html_scenarios():
    """Create test HTML scenarios for different special pricing patterns."""
    
    scenarios = {
        'strikethrough_pricing': """
        <div class="product-price">
            <del>£15.99</del>
            <span class="sale-price">£12.99</span>
        </div>
        """,
        
        'was_now_pricing': """
        <div class="price-container">
            <span>Was £20.50, now £17.25</span>
        </div>
        """,
        
        'offer_label_pricing': """
        <div class="special-offer">
            <span class="offer-badge">SPECIAL OFFER</span>
            <span class="price">£8.99</span>
        </div>
        """,
        
        'delivery_special_pricing': """
        <div class="delivery-pricing">
            <h3>Delivery: <del>£25.00</del> £19.99</h3>
        </div>
        """,
        
        'multiple_prices_no_context': """
        <div class="price-section">
            <span>£15.99</span>
            <span>£12.99</span>
        </div>
        """,
        
        'amazon_deal_pricing': """
        <div class="a-price">
            <span class="a-price-strike">£29.99</span>
            <span class="a-price-current">£24.99</span>
        </div>
        """,
        
        'jj_member_pricing': """
        <div class="member-price">
            <span class="standard-price">£18.50</span>
            <span class="member-discount">Member price: £15.25</span>
        </div>
        """,
        
        'atoz_h3_delivery': """
        <h3>Delivery: Was £22.00 Now £18.50</h3>
        """,
        
        'percentage_discount': """
        <div class="discount-container">
            <span class="discount-badge">20% OFF</span>
            <span class="original-price">RRP £25.00</span>
            <span class="sale-price">£20.00</span>
        </div>
        """
    }
    
    return scenarios


async def test_special_pricing_scenarios():
    """Test the special pricing detection with various scenarios."""
    
    # Initialize the scraper
    config = Config()
    scraper = UKCateringScraper(config)
    
    scenarios = create_test_html_scenarios()
    
    print("Testing Special Pricing Detection")
    print("=" * 50)
    
    for scenario_name, html_content in scenarios.items():
        print(f"\nTesting: {scenario_name}")
        print("-" * 30)
        
        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Test with different sites
        for site_name in ['jjfoodservice', 'atoz_catering', 'amazon_uk']:
            print(f"\n  {site_name}:")
            
            try:
                # Test special offer detection
                special_prices = scraper._find_special_offer_prices(soup, site_name)
                if special_prices:
                    best_price = min(price for price, _ in special_prices)
                    print(f"    ✓ Special offers found: {special_prices}")
                    print(f"    ✓ Best price: £{best_price}")
                else:
                    print(f"    ✗ No special offers detected")
                
                # Test the extraction methods
                if site_name == 'jjfoodservice':
                    result = scraper._extract_jjfoodservice_data(soup)
                elif site_name == 'atoz_catering':
                    result = scraper._extract_atoz_catering_data(soup)
                elif site_name == 'amazon_uk':
                    result = scraper._extract_amazon_uk_data(soup)
                
                if result['price']:
                    print(f"    ✓ Extracted price: £{result['price']}")
                else:
                    print(f"    ✗ No price extracted")
                    
            except Exception as e:
                print(f"    ✗ Error: {e}")


def test_parse_uk_price_functionality():
    """Test the enhanced _parse_uk_price function."""
    
    config = Config()
    scraper = UKCateringScraper(config)
    
    print("\n\nTesting _parse_uk_price Functionality")
    print("=" * 50)
    
    test_cases = [
        ("£15.99", False, False, 15.99),
        ("Was £20.00 Now £15.99", False, True, 15.99),
        ("£25.50 £19.99", False, True, 19.99),
        ("Delivery: £12.50", True, False, 12.50),
        ("Collection: £10.00 Delivery: £12.50", True, False, 12.50),
        ("RRP £30.00 Sale £24.99", False, True, 24.99),
        ("Save £5.00! Was £25.00 Now £20.00", False, True, 20.00),
    ]
    
    for i, (price_text, prefer_delivery, detect_special, expected) in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{price_text}'")
        print(f"  prefer_delivery={prefer_delivery}, detect_special={detect_special}")
        
        # Create a mock element for testing
        mock_html = f"<span>{price_text}</span>"
        mock_element = BeautifulSoup(mock_html, 'html.parser').find('span')
        
        result = scraper._parse_uk_price(
            price_text, 
            prefer_delivery=prefer_delivery, 
            detect_special_offers=detect_special,
            element=mock_element
        )
        
        if result == expected:
            print(f"  ✓ Result: £{result} (Expected: £{expected})")
        else:
            print(f"  ✗ Result: £{result} (Expected: £{expected})")


def test_special_pricing_context():
    """Test the special pricing context detection."""
    
    config = Config()
    scraper = UKCateringScraper(config)
    
    print("\n\nTesting Special Pricing Context Detection")
    print("=" * 50)
    
    context_test_cases = [
        ('<div class="sale"><del>£20.00</del><span>£15.99</span></div>', 'strikethrough'),
        ('<div>Was £25.00 Now £19.99</div>', 'was_now'),
        ('<div class="special-offer">£12.99</div>', 'offer_label'),
        ('<div><span style="text-decoration: line-through">£18.00</span>£14.99</div>', 'inline_strikethrough'),
    ]
    
    for i, (html_content, test_type) in enumerate(context_test_cases, 1):
        print(f"\nTest {i}: {test_type}")
        print(f"  HTML: {html_content}")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        element = soup.find(['span', 'div'])
        
        if element:
            context = scraper._extract_special_pricing_context(element)
            print(f"  ✓ Context: {context}")
        else:
            print(f"  ✗ No element found")


if __name__ == "__main__":
    print("UK Scraper Special Pricing Test Suite")
    print("=" * 60)
    
    # Test the price parsing functionality
    test_parse_uk_price_functionality()
    
    # Test special pricing context detection
    test_special_pricing_context()
    
    # Test full scenarios
    asyncio.run(test_special_pricing_scenarios())
    
    print("\n" + "=" * 60)
    print("Test suite completed!")
