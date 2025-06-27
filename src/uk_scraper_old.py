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
            'sold out'
        ]
        
        page_text = soup.get_text().lower()
        for indicator in availability_indicators:
            if indicator in page_text:
                result['availability'] = False
                break
        
        return result
    
    def _extract_atoz_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from A to Z Catering."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # A to Z Catering shows prices like "Delivery:£X.XX Collection:£Y.YY"
        # We'll prioritize the lower price (usually collection)
        
        price_text = soup.get_text()
        
        # Look for delivery and collection prices
        delivery_match = re.search(r'delivery:?\s*£(\d+\.?\d*)', price_text, re.IGNORECASE)
        collection_match = re.search(r'collection:?\s*£(\d+\.?\d*)', price_text, re.IGNORECASE)
        
        prices = []
        if delivery_match:
            try:
                prices.append(float(delivery_match.group(1)))
            except ValueError:
                pass
        
        if collection_match:
            try:
                prices.append(float(collection_match.group(1)))
            except ValueError:
                pass
        
        # If we found prices, use the lowest one
        if prices:
            result['price'] = min(prices)
        else:
            # Fallback to general price extraction
            price_selectors = [
                '.price',
                '.product-price',
                'span:contains("£")',
                '.price-value'
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
                    logger.debug(f"Error with A to Z price selector {selector}: {e}")
        
        # Extract title - A to Z often has product names in links
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
                    title = element.get_text(strip=True)
                    # Clean up the title
                    if len(title) > 5 and 'A to Z' not in title:
                        result['title'] = title
                        break
            except Exception as e:
                logger.debug(f"Error with A to Z title selector {selector}: {e}")
        
        # Check availability - look for "Add To Basket" button
        add_to_basket = soup.find(text=re.compile('Add To Basket', re.IGNORECASE))
        if not add_to_basket:
            # Also check for out of stock indicators
            out_of_stock_indicators = [
                'out of stock',
                'unavailable',
                'not available',
                'sold out'
            ]
            
            page_text = soup.get_text().lower()
            for indicator in out_of_stock_indicators:
                if indicator in page_text:
                    result['availability'] = False
                    break
        
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
            '.a-price-current .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '.a-price-range',
            '.a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen'
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
            'h1.a-size-large'
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
        availability_text = soup.get_text().lower()
        if any(phrase in availability_text for phrase in ['out of stock', 'currently unavailable', 'not available']):
            result['availability'] = False
        
        return result
    
    def _extract_tesco_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from Tesco."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # Tesco price selectors
        price_selectors = [
            '.price-control-wrapper .value',
            '.price-per-sellable-unit .value',
            '.price-per-quantity-weight .value',
            '[data-testid="price-current-value"]',
            '.price-current',
            '.product-price .price'
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
                logger.debug(f"Error with Tesco price selector {selector}: {e}")
        
        # Extract title
        title_selectors = [
            'h1[data-testid="product-title"]',
            '.product-details-tile h1',
            '.product-title',
            'h1.product-name'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with Tesco title selector {selector}: {e}")
        
        return result
    
    def _extract_sainsburys_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from Sainsburys."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # Sainsburys price selectors
        price_selectors = [
            '.pd__cost__current-price',
            '.pd__cost .pd__cost__retail-price',
            '.pricing__now-price',
            '.product-price__current',
            '[data-testid="pd-retail-price"]',
            '.price-per-unit'
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
                logger.debug(f"Error with Sainsburys price selector {selector}: {e}")
        
        # Extract title
        title_selectors = [
            '.pd__header h1',
            'h1[data-testid="pd-product-name"]',
            '.product-name',
            '.pd__product-name'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with Sainsburys title selector {selector}: {e}")
        
        return result
    
    def _extract_booker_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from Booker."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # Booker price selectors
        price_selectors = [
            '.price',
            '.product-price',
            '.price-current',
            '.selling-price',
            '[data-testid="price"]',
            '.product-tile-price'
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
                logger.debug(f"Error with Booker price selector {selector}: {e}")
        
        # Extract title
        title_selectors = [
            'h1',
            '.product-title',
            '.product-name',
            '.product-description h1',
            '[data-testid="product-title"]'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with Booker title selector {selector}: {e}")
        
        return result
    
    async def scrape_product_price(self, url: str, site_name: str = None) -> Dict[str, Any]:
        """Enhanced scraping for UK catering sites."""
        result = {
            'success': False,
            'price': None,
            'currency': 'GBP',
            'title': None,
            'availability': None,
            'url': url,
            'error': None
        }
        
        try:
            # Auto-detect site if not provided
            if not site_name:
                site_name = self._detect_site(url)
                if not site_name:
                    result['error'] = "Could not detect site from URL"
                    return result
            
            # Check if site is enabled
            if not self.config.is_site_enabled(site_name):
                result['error'] = f"Site {site_name} is disabled"
                return result
            
            # Fetch page content
            html_content = await self._fetch_page(url)
            if not html_content:
                result['error'] = "Failed to fetch page content"
                return result
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Use specialized extraction based on site
            if site_name == 'jjfoodservice':
                extracted_data = self._extract_jjfoodservice_data(soup)
            elif site_name == 'atoz_catering':
                extracted_data = self._extract_atoz_data(soup)
            elif site_name == 'amazon_uk':
                extracted_data = self._extract_amazon_uk_data(soup)
            elif site_name == 'tesco':
                extracted_data = self._extract_tesco_data(soup)
            elif site_name == 'sainsburys':
                extracted_data = self._extract_sainsburys_data(soup)
            elif site_name == 'booker':
                extracted_data = self._extract_booker_data(soup)
            else:
                # Fall back to general extraction
                return await super().scrape_product_price(url, site_name)
            
            if extracted_data['price'] is None:
                result['error'] = "Could not extract price from page"
                return result
            
            result.update({
                'success': True,
                'price': extracted_data['price'],
                'currency': extracted_data.get('currency', 'GBP'),
                'title': extracted_data.get('title'),
                'availability': extracted_data.get('availability', True)
            })
            
            logger.info(f"Successfully scraped {site_name}: £{extracted_data['price']}")
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _detect_site(self, url: str) -> Optional[str]:
        """Detect which UK catering site this URL belongs to."""
        url_lower = url.lower()
        
        if 'jjfoodservice.com' in url_lower:
            return 'jjfoodservice'
        elif 'atoz-catering.co.uk' in url_lower:
            return 'atoz_catering'
        elif 'amazon.co.uk' in url_lower:
            return 'amazon_uk'
        elif 'tesco.com' in url_lower:
            return 'tesco'
        elif 'sainsburys.co.uk' in url_lower:
            return 'sainsburys'
        elif 'booker.co.uk' in url_lower:
            return 'booker'
        
        # Fall back to parent detection for other sites
        return super()._detect_site(url)
