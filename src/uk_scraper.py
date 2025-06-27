"""
Specialized scrapers for UK catering supply sites
"""

import re
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from .scraper import PriceScraper

logger = logging.getLogger(__name__)


class UKCateringScraper(PriceScraper):
    """Specialized scraper for UK catering supply websites."""
    
    def _parse_uk_price(self, price_text: str) -> Optional[float]:
        """Parse UK price format with £ symbol."""
        if not price_text:
            return None
        
        # Remove common text and normalize
        price_text = price_text.lower()
        price_text = re.sub(r'delivery:|collection:|was:|now:|offer:|from:', '', price_text)
        
        # Find price with £ symbol
        price_match = re.search(r'£(\d+\.?\d*)', price_text)
        if price_match:
            try:
                return float(price_match.group(1))
            except ValueError:
                pass
        
        # Try without £ symbol but with decimal
        price_match = re.search(r'(\d+\.\d{2})', price_text)
        if price_match:
            try:
                return float(price_match.group(1))
            except ValueError:
                pass
        
        return None
    
    def _extract_jjfoodservice_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from JJ Food Service."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # Try multiple selectors for price
        price_selectors = [
            '.price',
            '.product-price',
            '[data-testid="price"]',
            '.price-value',
            '.current-price',
            '.product-card-price',
            'span:contains("£")',
            '.cost'
        ]
        
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    price = self._parse_uk_price(price_text)
                    if price is not None:
                        result['price'] = price
                        logger.info(f"Successfully scraped jjfoodservice: £{price}")
                        break
                if result['price'] is not None:
                    break
            except Exception as e:
                logger.debug(f"Error with JJ Food Service price selector {selector}: {e}")
        
        # Try to extract title
        title_selectors = [
            'h1',
            '.product-title',
            '.product-name',
            '[data-testid="product-title"]',
            '.product-card-title',
            'title'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with JJ Food Service title selector {selector}: {e}")
        
        # Check availability
        availability_indicators = [
            'out of stock',
            'unavailable',
            'not available',
            'temporarily unavailable'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in availability_indicators:
            if indicator in page_text:
                result['availability'] = False
                break
        
        return result
    
    def _extract_atoz_catering_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from A to Z Catering."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # A to Z Catering specific selectors
        price_selectors = [
            '.price',
            '.product-price',
            '.delivery-price',
            '.collection-price',
            'span:contains("£")',
            '.price-value',
            '.cost',
            '.selling-price'
        ]
        
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    # Skip if it contains "delivery" or "collection" but no price
                    if ('delivery' in price_text.lower() or 'collection' in price_text.lower()) and '£' not in price_text:
                        continue
                    
                    price = self._parse_uk_price(price_text)
                    if price is not None:
                        result['price'] = price
                        logger.info(f"Successfully scraped atoz_catering: £{price}")
                        break
                if result['price'] is not None:
                    break
            except Exception as e:
                logger.debug(f"Error with A to Z price selector {selector}: {e}")
        
        # Extract title
        title_selectors = [
            'h1',
            '.product-title',
            '.product-name',
            'a[href*="/products/product/"]',
            '.product-link',
            'title'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with A to Z title selector {selector}: {e}")
        
        # Check availability - A to Z specific indicators
        availability_indicators = [
            'out of stock',
            'unavailable',
            'not available',
            'temporarily unavailable',
            'contact us for availability'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in availability_indicators:
            if indicator in page_text:
                result['availability'] = False
                break
        
        # Check if "Add to Basket" button is present (indicates availability)
        add_to_basket = soup.select_one('.add-to-basket, button:contains("Add To Basket")')
        if not add_to_basket and result['availability']:
            # If no add to basket button and no explicit availability info, assume unavailable
            out_of_stock_indicators = soup.select('.out-of-stock, .unavailable')
            if out_of_stock_indicators:
                result['availability'] = False
        
        return result
    
    def _extract_amazon_uk_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from Amazon UK."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # Amazon UK price selectors
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '.a-price-range',
            '.a-price.a-text-price.a-size-medium.apexPriceToPay',
            '.a-price-current',
            'span.a-price.a-text-price.a-size-medium'
        ]
        
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    price = self._parse_uk_price(price_text)
                    if price is not None:
                        result['price'] = price
                        break
                if result['price'] is not None:
                    break
            except Exception as e:
                logger.debug(f"Error with Amazon UK price selector {selector}: {e}")
        
        # Extract title
        title_selectors = [
            '#productTitle',
            '.product-title',
            'h1.a-size-large',
            'h1'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with Amazon UK title selector {selector}: {e}")
        
        # Check availability
        availability_selectors = [
            '#availability span',
            '.a-size-medium.a-color-success',
            '.a-size-medium.a-color-state',
            '#availability .a-declarative'
        ]
        
        for selector in availability_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    availability_text = element.get_text().lower()
                    if any(phrase in availability_text for phrase in ['out of stock', 'unavailable', 'not available']):
                        result['availability'] = False
                    break
            except Exception as e:
                logger.debug(f"Error with Amazon UK availability selector {selector}: {e}")
        
        return result

    async def scrape_product(self, product_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Scrape prices for a product from all configured sites."""
        results = {}
        urls = product_data.get('urls', {})
        
        for site_name, url in urls.items():
            try:
                # Only process sites we support
                if site_name not in ['jjfoodservice', 'atoz_catering', 'amazon_uk']:
                    logger.warning(f"Skipping unsupported site: {site_name}")
                    continue
                    
                html_content = await self._fetch_page(url)
                if not html_content:
                    results[site_name] = {
                        'success': False,
                        'error': 'Failed to fetch page',
                        'price': None,
                        'currency': 'GBP'
                    }
                    continue
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Route to appropriate extraction method
                if site_name == 'jjfoodservice':
                    extracted_data = self._extract_jjfoodservice_data(soup)
                elif site_name == 'atoz_catering':
                    extracted_data = self._extract_atoz_catering_data(soup)
                elif site_name == 'amazon_uk':
                    extracted_data = self._extract_amazon_uk_data(soup)
                else:
                    # Fallback to generic extraction
                    extracted_data = self._extract_generic_data(soup, site_name)
                
                if extracted_data['price'] is not None:
                    results[site_name] = {
                        'success': True,
                        'price': extracted_data['price'],
                        'currency': extracted_data['currency'],
                        'title': extracted_data.get('title'),
                        'availability': extracted_data.get('availability', True)
                    }
                else:
                    results[site_name] = {
                        'success': False,
                        'error': 'Could not extract price',
                        'price': None,
                        'currency': 'GBP'
                    }
                    
            except Exception as e:
                logger.error(f"Error scraping {site_name}: {e}")
                results[site_name] = {
                    'success': False,
                    'error': str(e),
                    'price': None,
                    'currency': 'GBP'
                }
        
        return results
