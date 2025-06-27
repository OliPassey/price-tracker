#!/usr/bin/env python3
"""
Debug script specifically for A to Z Catering pricing issues
"""

import requests
from bs4 import BeautifulSoup
import re
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def fetch_and_analyze_atoz_page(url):
    """Fetch and analyze the A to Z page to identify pricing issues."""
    
    print(f"Analyzing A to Z page: {url}")
    print("=" * 80)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print("Failed to fetch page")
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Find all elements containing prices
        print("\n1. ALL PRICE ELEMENTS FOUND:")
        print("-" * 40)
        price_pattern = re.compile(r'£\d+\.?\d*')
        price_elements = soup.find_all(string=price_pattern)
        
        for i, price_text in enumerate(price_elements):
            parent = price_text.parent if hasattr(price_text, 'parent') else None
            parent_class = parent.get('class', []) if parent else []
            parent_tag = parent.name if parent else 'N/A'
            
            print(f"  {i+1:2d}. '{price_text.strip()}' in <{parent_tag}> class={parent_class}")
        
        # 2. Check for delivery-specific elements
        print("\n2. DELIVERY-RELATED ELEMENTS:")
        print("-" * 40)
        delivery_keywords = ['delivery', 'delivered']
        
        for keyword in delivery_keywords:
            elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
            for elem in elements[:5]:  # Show first 5
                parent = elem.parent if hasattr(elem, 'parent') else None
                parent_class = parent.get('class', []) if parent else []
                text = elem.strip()[:100]
                print(f"  '{text}' in class={parent_class}")
        
        # 3. Check h3 and h4 elements (A to Z specific)
        print("\n3. H3/H4 ELEMENTS WITH PRICES:")
        print("-" * 40)
        headers = soup.find_all(['h3', 'h4'])
        for header in headers:
            text = header.get_text(strip=True)
            if '£' in text:
                print(f"  <{header.name}>: {text}")
        
        # 4. Test specific selectors from our config
        print("\n4. TESTING OUR SELECTORS:")
        print("-" * 40)
        
        test_selectors = [
            '.delivery-price',
            '.price-delivery', 
            '.price',
            '.product-price',
            '.collection-price',
            'span:contains("£")',
            'h3:contains("Delivery")',
            'h4:contains("Delivery")',
            '*[class*="price"]'
        ]
        
        for selector in test_selectors:
            try:
                if ':contains(' in selector:
                    # Handle contains selectors differently
                    if 'h3:contains("Delivery")' == selector:
                        elements = [h for h in soup.find_all('h3') if 'delivery' in h.get_text().lower()]
                    elif 'h4:contains("Delivery")' == selector:
                        elements = [h for h in soup.find_all('h4') if 'delivery' in h.get_text().lower()]
                    elif 'span:contains("£")' == selector:
                        elements = [s for s in soup.find_all('span') if '£' in s.get_text()]
                    else:
                        elements = []
                else:
                    elements = soup.select(selector)
                
                if elements:
                    print(f"  ✓ {selector} -> {len(elements)} elements:")
                    for i, elem in enumerate(elements[:3]):  # Show first 3
                        text = elem.get_text(strip=True)
                        if '£' in text:
                            print(f"     [{i+1}] {text}")
                else:
                    print(f"  ✗ {selector} -> No elements")
                    
            except Exception as e:
                print(f"  ⚠ {selector} -> Error: {e}")
        
        # 5. Look for the specific prices mentioned (12.99 and 1.39)
        print("\n5. SPECIFIC PRICE ANALYSIS:")
        print("-" * 40)
        
        if '12.99' in response.text:
            print("✓ £12.99 found in page content")
            # Find context around 12.99
            matches = list(re.finditer(r'12\.99', response.text))
            for match in matches[:3]:  # Show first 3 occurrences
                start = max(0, match.start() - 100)
                end = min(len(response.text), match.end() + 100)
                context = response.text[start:end].replace('\n', ' ').replace('\t', ' ')
                print(f"  Context: ...{context}...")
        else:
            print("✗ £12.99 NOT found in page content")
        
        if '1.39' in response.text:
            print("✓ £1.39 found in page content")
            # Find context around 1.39
            matches = list(re.finditer(r'1\.39', response.text))
            for match in matches[:3]:  # Show first 3 occurrences
                start = max(0, match.start() - 100)
                end = min(len(response.text), match.end() + 100)
                context = response.text[start:end].replace('\n', ' ').replace('\t', ' ')
                print(f"  Context: ...{context}...")
        else:
            print("✗ £1.39 NOT found in page content")
        
        # 6. Try to simulate our current parsing logic
        print("\n6. SIMULATING CURRENT PARSING LOGIC:")
        print("-" * 40)
        
        # Test our general price selectors
        general_selectors = [
            '.price',
            '.product-price', 
            'span:contains("£")',
            '.price-value',
        ]
        
        found_prices = []
        for selector in general_selectors:
            try:
                if selector == 'span:contains("£")':
                    elements = [s for s in soup.find_all('span') if '£' in s.get_text()]
                else:
                    elements = soup.select(selector)
                
                for element in elements:
                    price_text = element.get_text(strip=True)
                    if '£' in price_text:
                        # Extract price using regex
                        price_matches = re.findall(r'£(\d+\.?\d*)', price_text)
                        for match in price_matches:
                            try:
                                price_value = float(match)
                                found_prices.append((price_value, selector, price_text))
                            except ValueError:
                                pass
                                
            except Exception as e:
                print(f"Error with {selector}: {e}")
        
        print(f"Found {len(found_prices)} prices total:")
        for price, selector, text in found_prices:
            print(f"  £{price} from '{selector}': {text[:50]}")
        
        if found_prices:
            # Show what our current logic would select
            min_price = min(price for price, _, _ in found_prices)
            max_price = max(price for price, _, _ in found_prices)
            last_price = found_prices[-1][0] if found_prices else None
            
            print(f"\nCurrent logic would likely select:")
            print(f"  Minimum price: £{min_price}")
            print(f"  Maximum price: £{max_price}")
            print(f"  Last price found: £{last_price}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    url = "https://www.atoz-catering.co.uk/products/product/coca-cola-cans--coke-gb---24"
    fetch_and_analyze_atoz_page(url)
