"""
Specialized scrapers for UK catering supply sites
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from bs4 import BeautifulSoup, Tag
from .scraper import PriceScraper

logger = logging.getLogger(__name__)


class UKCateringScraper(PriceScraper):
    """Specialized scraper for UK catering supply websites."""
    
    def _extract_special_pricing_context(self, element: Tag) -> Dict[str, Any]:
        """Extract special pricing context from an element and its surroundings."""
        context = {
            'has_strikethrough': False,
            'has_offer_label': False,
            'has_was_now': False,
            'prices': [],
            'price_types': []
        }
        
        # Get parent elements to check for special pricing context
        parents = [element] + [p for p in element.parents if p.name][:3]  # Check up to 3 levels up
        
        for parent in parents:
            parent_text = parent.get_text().lower() if parent else ""
            
            # Check for strikethrough pricing
            strikethrough_elements = parent.find_all(['del', 's', 'strike']) if parent else []
            if strikethrough_elements:
                context['has_strikethrough'] = True
                for strike_elem in strikethrough_elements:
                    strike_price = self._parse_uk_price(strike_elem.get_text())
                    if strike_price:
                        context['prices'].append(strike_price)
                        context['price_types'].append('was_price')
            
            # Check for offer/sale/discount labels
            offer_patterns = [
                r'\bsale\b', r'\boffer\b', r'\bdeal\b', r'\bdiscount\b', 
                r'\bspecial\b', r'\bpromo\b', r'\breduced\b', r'\bsave\b',
                r'\bwas\s*£', r'\bnow\s*£', r'\b\d+%\s*off\b'
            ]
            
            for pattern in offer_patterns:
                if re.search(pattern, parent_text):
                    context['has_offer_label'] = True
                    break
            
            # Look for "was/now" pricing patterns
            was_now_match = re.search(r'was\s*£([\d.]+).*?now\s*£([\d.]+)', parent_text, re.IGNORECASE)
            if was_now_match:
                context['has_was_now'] = True
                was_price = float(was_now_match.group(1))
                now_price = float(was_now_match.group(2))
                context['prices'].extend([was_price, now_price])
                context['price_types'].extend(['was_price', 'now_price'])
        
        return context
    
    def _parse_uk_price(self, price_text: str, prefer_delivery: bool = False) -> Optional[float]:
        """Simple, conservative UK price parsing - just extract the first reasonable price."""
        if not price_text:
            return None
        
        # Skip very long text blocks that are unlikely to contain just prices
        if len(price_text) > 100:
            return None
        
        # Check if this is delivery or collection pricing
        is_delivery = 'delivery' in price_text.lower()
        is_collection = 'collection' in price_text.lower()
        
        # If we prefer delivery and this is explicitly collection, skip it
        if prefer_delivery and is_collection and not is_delivery:
            return None
        
        # Simple regex to find prices - be very specific
        price_match = re.search(r'£(\d{1,3}(?:\.\d{2})?)', price_text)
        
        if price_match:
            try:
                price_val = float(price_match.group(1))
                # Only accept reasonable food product prices
                if 2.0 <= price_val <= 100.0:
                    return price_val
            except ValueError:
                pass
        
        return None
    
    def _find_special_offer_prices(self, soup: BeautifulSoup, site_name: str) -> List[Tuple[float, str]]:
        """Find special offer prices using enhanced selectors."""
        special_prices = []
        
        # Enhanced selectors for special offers
        special_offer_selectors = [
            # General special offer containers
            '.special-offer', '.sale-price', '.offer-price', '.discount-price',
            '.promo-price', '.reduced-price', '.deal-price',
            
            # Strikethrough and comparison pricing
            'del:contains("£"), s:contains("£"), strike:contains("£")',
            '.was-price', '.original-price', '.rrp-price',
            
            # Was/Now pricing containers
            '.was-now-pricing', '.price-comparison', '.before-after-price',
            
            # Sale badges and labels
            '.sale-badge', '.offer-badge', '.discount-badge',
            '*[class*="sale"]:contains("£")',
            '*[class*="offer"]:contains("£")',
            '*[class*="discount"]:contains("£")',
            
            # Site-specific patterns
            '.product-price-wrapper', '.price-container', '.pricing-section'
        ]
        
        if site_name == 'atoz_catering':
            # A to Z specific selectors - prioritize the offer price class
            special_offer_selectors.extend([
                '.my-price.price-offer',  # Primary A to Z offer price selector
                'h3:contains("£")', 'h4:contains("£")',
                '.delivery-price-special', '.collection-price-special',
                '*[style*="text-decoration: line-through"]',
                '*[style*="text-decoration:line-through"]'
            ])
        elif site_name == 'jjfoodservice':
            # JJ Food Service specific selectors
            special_offer_selectors.extend([
                '.member-price', '.trade-price', '.bulk-price',
                '.quantity-discount', '.volume-discount'
            ])
        elif site_name == 'amazon_uk':
            # Amazon UK specific selectors
            special_offer_selectors.extend([
                '.a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen',
                '.a-price-strike .a-offscreen',
                '#priceblock_dealprice', '#priceblock_saleprice',
                '.a-price-was', '.a-price-save'
            ])
        
        for selector in special_offer_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    if '£' in price_text:
                        price = self._parse_uk_price(price_text, detect_special_offers=True, element=element)
                        if price:
                            special_prices.append((price, selector))
            except Exception as e:
                logger.debug(f"Error with special offer selector {selector}: {e}")
        
        return special_prices
    
    def _extract_jjfoodservice_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from JJ Food Service - simplified approach."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # First, try to find elements with Price in class name and extract delivery price
        price_elements = soup.select('[class*="Price"]')
        logger.debug(f"JJ Food Service: Found {len(price_elements)} price elements")
        
        for element in price_elements:
            text = element.get_text(strip=True)
            logger.debug(f"JJ Food Service: Checking price element text: '{text[:100]}'")
            
            # Look for delivery price in concatenated strings like "Collection:£10.49£4.62 per kgDelivery:£11.79£5.19 per kg"
            delivery_match = re.search(r'Delivery:£(\d{1,3}\.\d{2})', text, re.IGNORECASE)
            if delivery_match:
                price_val = float(delivery_match.group(1))
                result['price'] = price_val
                logger.info(f"JJ Food Service: Found delivery price £{price_val} in price element")
                # extract title
                title_el = soup.select_one('h1')
                if title_el:
                    result['title'] = title_el.get_text(strip=True)
                return result
        
        # Second, attempt regex-based parsing of delivery price from raw page text
        page_text = soup.get_text(separator=' ')
        logger.debug(f"JJ Food Service page_text snippet: {page_text[:500]!r}")
        
        # Look for delivery price patterns in the text
        if 'DELIVERY' in page_text or 'delivery' in page_text:
            logger.debug(f"Found 'DELIVERY' in page text, looking for price patterns...")
            delivery_section = page_text[page_text.lower().find('delivery'):page_text.lower().find('delivery')+100]
            logger.debug(f"Delivery section: {delivery_section!r}")
        
        # Try multiple patterns for delivery price (based on actual HTML structure)
        delivery_patterns = [
            r'Delivery:£(\d{1,3}\.\d{2})',     # Delivery:£11.79 (actual format found)
            r'DELIVERY:£(\d{1,3}\.\d{2})',     # DELIVERY:£11.79
            r'delivery:£(\d{1,3}\.\d{2})',     # delivery:£11.79
            r'DELIVERY:\s*£(\d{1,3}\.\d{2})',  # DELIVERY: £11.79 (with space)
            r'delivery:\s*£(\d{1,3}\.\d{2})',  # delivery: £11.79 (with space)
        ]
        
        for pattern in delivery_patterns:
            logger.debug(f"JJ Food Service: Trying pattern: {pattern}")
            delivery_match = re.search(pattern, page_text, re.IGNORECASE)
            if delivery_match:
                price_val = float(delivery_match.group(1))
                result['price'] = price_val
                logger.info(f"JJ Food Service: Parsed delivery price £{price_val} via regex pattern: {pattern}")
                # extract title
                title_el = soup.select_one('h1')
                if title_el:
                    result['title'] = title_el.get_text(strip=True)
                return result
            else:
                logger.debug(f"JJ Food Service: Pattern {pattern} did not match")
        # Otherwise, try very specific selectors first - likely to contain prices
        specific_selectors = [
            '.price-delivery',  # Delivery price specifically
            '.delivery-price',  # Alternative delivery price
            '.price',           # General price class
        ]
        
        for selector in specific_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    # Only process short text snippets that likely contain just prices
                    if '£' in price_text and len(price_text) < 30:
                        price = self._parse_uk_price(price_text, prefer_delivery=True)
                        if price is not None:
                            result['price'] = price
                            logger.info(f"JJ Food Service: Found price £{price} with selector '{selector}' from text: '{price_text}'")
                            break
                if result['price'] is not None:
                    break
            except Exception as e:
                logger.debug(f"Error with JJ Food Service selector {selector}: {e}")
        
        # Extract title
        title_selectors = ['h1', '.product-title', '.product-name']
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with JJ Food Service title selector {selector}: {e}")
        
        return result
    
    def _extract_atoz_catering_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract data specifically from A to Z Catering - prioritize delivery pricing using regex parse."""
        result = {'price': None, 'title': None, 'availability': True, 'currency': 'GBP'}
        # First, attempt to parse delivery price directly from page text
        page_text = soup.get_text(separator=' ')
        delivery_match = re.search(r'Delivery:\s*£(\d{1,3}\.\d{2})', page_text)
        if delivery_match:
            price_val = float(delivery_match.group(1))
            result['price'] = price_val
            logger.info(f"A to Z Catering: Parsed delivery price £{price_val} via regex")
            # extract title
            title_el = soup.select_one('h1')
            if title_el:
                result['title'] = title_el.get_text(strip=True)
            return result
        
        # 1) Delivery-specific selectors
        for selector in ['.delivery-price', '.price-delivery']:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    price = self._parse_uk_price(text, prefer_delivery=True)
                    if price is not None:
                        result['price'] = price
                        logger.info(f"A to Z Catering: Found delivery price £{price} from {selector}")
                        return result
            except Exception as e:
                logger.debug(f"Error with A to Z delivery selector {selector}: {e}")

        # 2) Main offer selector (fallback to collection price)
        for selector in ['.my-price.price-offer']:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    price = self._parse_uk_price(text)
                    if price is not None:
                        result['price'] = price
                        logger.info(f"A to Z Catering: Found collection price £{price} from {selector}")
                        return result
            except Exception as e:
                logger.debug(f"Error with A to Z main selector {selector}: {e}")

        # 3) Fallback general selectors
        for selector in ['.price', '.product-price']:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    price = self._parse_uk_price(text)
                    if price is not None:
                        result['price'] = price
                        logger.info(f"A to Z Catering: Fallback parsed price £{price} from {selector}")
                        return result
            except Exception as e:
                logger.debug(f"Error with A to Z fallback selector {selector}: {e}")
        
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
        """Extract data specifically from Amazon UK with enhanced special pricing detection."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # First, check for special offer prices using enhanced detection
        special_prices = self._find_special_offer_prices(soup, 'amazon_uk')
        if special_prices:
            # Use the lowest special offer price found
            best_special_price = min(price for price, _ in special_prices)
            result['price'] = best_special_price
            logger.info(f"Successfully scraped amazon_uk special offer price: £{best_special_price}")
            return result
        
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
                    price = self._parse_uk_price(price_text, detect_special_offers=True, element=element)
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

    def _extract_generic_data(self, soup: BeautifulSoup, site_name: str) -> Dict[str, Any]:
        """Generic data extraction for UK sites not specifically implemented."""
        result = {
            'price': None,
            'title': None,
            'availability': True,
            'currency': 'GBP'
        }
        
        # Generic price selectors
        price_selectors = [
            '.price',
            '.product-price',
            '[data-testid="price"]',
            '.price-value',
            '.current-price',
            'span:contains("£")',
            '.cost',
            '.selling-price'
        ]
        
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    price = self._parse_uk_price(price_text)
                    if price is not None:
                        result['price'] = price
                        logger.info(f"Successfully scraped {site_name} generic price: £{price}")
                        break
                if result['price'] is not None:
                    break
            except Exception as e:
                logger.debug(f"Error with generic price selector {selector}: {e}")
        
        # Generic title selectors
        title_selectors = [
            'h1',
            '.product-title',
            '.product-name',
            '[data-testid="product-title"]',
            'title'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    result['title'] = element.get_text(strip=True)
                    break
            except Exception as e:
                logger.debug(f"Error with generic title selector {selector}: {e}")
        
        return result

    async def scrape_product_price(self, url: str, site_name: str = None) -> Dict[str, Any]:
        """Scrape price for a single product from a URL using UK-specific logic."""
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
            # Validate that this is a supported UK site
            if site_name not in ['jjfoodservice', 'atoz_catering', 'amazon_uk']:
                result['error'] = f"Unsupported site for UK scraper: {site_name}"
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
                result.update({
                    'success': True,
                    'price': extracted_data['price'],
                    'title': extracted_data.get('title'),
                    'availability': extracted_data.get('availability')
                })
                logger.info(f"Successfully scraped {site_name}: £{extracted_data['price']}")
            else:
                result['error'] = "Could not extract price from page"
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            result['error'] = str(e)
        
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
