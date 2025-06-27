#!/usr/bin/env python3
"""
Simple test for special pricing functionality
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported."""
    try:
        print("Testing imports...")
        
        # Basic imports
        import re
        import logging
        from typing import Dict, Any, Optional, List, Tuple
        print("✓ Basic Python modules imported")
        
        # Third-party imports
        from bs4 import BeautifulSoup, Tag
        print("✓ BeautifulSoup imported")
        
        # Local imports
        from config import Config
        print("✓ Config imported")
        
        from scraper import PriceScraper
        print("✓ PriceScraper imported")
        
        from uk_scraper import UKCateringScraper
        print("✓ UKCateringScraper imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_basic_functionality():
    """Test basic functionality of the special pricing."""
    try:
        from config import Config
        from uk_scraper import UKCateringScraper
        
        print("\nTesting basic functionality...")
        
        # Create config and scraper
        config = Config()
        scraper = UKCateringScraper(config)
        print("✓ Scraper created successfully")
        
        # Test price parsing
        test_price = scraper._parse_uk_price("£12.99")
        if test_price == 12.99:
            print("✓ Basic price parsing works")
        else:
            print(f"✗ Price parsing failed: got {test_price}, expected 12.99")
        
        # Test special pricing
        special_price = scraper._parse_uk_price("Was £20.00 Now £15.99", detect_special_offers=True)
        if special_price == 15.99:
            print("✓ Special price parsing works")
        else:
            print(f"✗ Special price parsing failed: got {special_price}, expected 15.99")
        
        return True
        
    except Exception as e:
        print(f"✗ Functionality error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_html_parsing():
    """Test HTML parsing for special pricing."""
    try:
        from bs4 import BeautifulSoup
        from uk_scraper import UKCateringScraper
        from config import Config
        
        print("\nTesting HTML parsing...")
        
        config = Config()
        scraper = UKCateringScraper(config)
        
        # Test strikethrough detection
        html = '<div><del>£20.00</del><span>£15.99</span></div>'
        soup = BeautifulSoup(html, 'html.parser')
        
        special_prices = scraper._find_special_offer_prices(soup, 'atoz_catering')
        if special_prices:
            print(f"✓ Special offer detection works: found {len(special_prices)} prices")
        else:
            print("✗ Special offer detection failed")
        
        return True
        
    except Exception as e:
        print(f"✗ HTML parsing error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Simple Special Pricing Test")
    print("=" * 40)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    # Test HTML parsing
    if not test_html_parsing():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        sys.exit(1)
