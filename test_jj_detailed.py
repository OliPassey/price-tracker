#!/usr/bin/env python3
import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup

async def test_jj_patterns():
    url = "https://www.jjfoodservice.com/product/London-Enfield/BAC002/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
            
    print(f"HTML content length: {len(html)}")
    
    # Look for various keywords
    keywords = ['DELIVERY', 'delivery', 'COLLECTION', 'collection', '£10.49', '£11.79', '10.49', '11.79']
    
    for keyword in keywords:
        if keyword in html:
            print(f"'{keyword}' FOUND in HTML")
            # Find context around the keyword
            index = html.find(keyword)
            start = max(0, index - 100)
            end = min(len(html), index + 100)
            context = html[start:end]
            print(f"Context: ...{context}...")
            print()
        else:
            print(f"'{keyword}' NOT found in HTML")
    
    # Look for any price-like patterns
    price_patterns = re.findall(r'£?(\d{1,3}\.\d{2})', html)
    print(f"\nAll price patterns found: {price_patterns}")
    
    # Try to find price elements using BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Look for specific CSS classes that might contain prices
    price_selectors = [
        '.price', '.product-price', '.delivery-price', '.price-delivery',
        '[class*="price"]', '[class*="Price"]'
    ]
    
    for selector in price_selectors:
        elements = soup.select(selector)
        if elements:
            print(f"\nFound elements with selector '{selector}':")
            for elem in elements[:5]:  # Show first 5
                print(f"  - {elem.get_text(strip=True)}")

if __name__ == "__main__":
    asyncio.run(test_jj_patterns())
