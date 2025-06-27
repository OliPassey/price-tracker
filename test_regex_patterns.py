#!/usr/bin/env python3
"""
Test the exact regex patterns against the actual HTML content
"""

import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup

async def test_jj_patterns():
    url = "https://www.jjfoodservice.com/product/London-Enfield/BAC002/"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html_content = await response.text()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    page_text = soup.get_text(separator=' ')
    
    print(f"Page text length: {len(page_text)}")
    
    # Find the section with delivery info
    delivery_start = page_text.lower().find('delivery')
    if delivery_start >= 0:
        delivery_section = page_text[delivery_start:delivery_start+200]
        print(f"Delivery section: {delivery_section!r}")
    
    # Test the exact patterns
    delivery_patterns = [
        r'Delivery:£(\d{1,3}\.\d{2})',     # Delivery:£11.79
        r'DELIVERY:£(\d{1,3}\.\d{2})',     # DELIVERY:£11.79
        r'delivery:£(\d{1,3}\.\d{2})',     # delivery:£11.79
        r'DELIVERY:\s*£(\d{1,3}\.\d{2})',  # DELIVERY: £11.79
        r'delivery:\s*£(\d{1,3}\.\d{2})',  # delivery: £11.79
    ]
    
    for pattern in delivery_patterns:
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            print(f"✅ Pattern '{pattern}' matched! Price: £{match.group(1)}")
            return float(match.group(1))
        else:
            print(f"❌ Pattern '{pattern}' did not match")
    
    print("No delivery patterns matched!")
    return None

if __name__ == "__main__":
    result = asyncio.run(test_jj_patterns())
    print(f"Final result: {result}")
