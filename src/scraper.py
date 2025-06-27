"""
Web scraping functionality for price tracking
"""

import asyncio
import aiohttp
import logging
import random
import re
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from .config import Config

logger = logging.getLogger(__name__)


class PriceScraper:
    """Base class for price scraping functionality."""
    
    def __init__(self, config: Config):
        self.config = config
        self.ua = UserAgent()
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(limit=self.config.max_concurrent_requests)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': self.ua.random}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_headers(self, url: str = None) -> Dict[str, str]:
        """Get request headers with random user agent and site-specific headers."""
        user_agents = self.config.user_agents
        if user_agents:
            user_agent = random.choice(user_agents)
        else:
            user_agent = self.ua.random
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
        }
        
        # Add site-specific headers
        if url:
            if 'amazon.co.uk' in url:
                headers.update({
                    'Referer': 'https://www.amazon.co.uk/',
                })
            elif 'jjfoodservice.com' in url:
                headers.update({
                    'Referer': 'https://www.jjfoodservice.com/',
                })
            elif 'atoz-catering.co.uk' in url:
                headers.update({
                    'Referer': 'https://www.atoz-catering.co.uk/',
                })
        
        return headers
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with retry logic and anti-bot measures."""
        base_delay = random.uniform(1, 3)  # Random delay between 1-3 seconds
        
        for attempt in range(self.config.retry_attempts):
            try:
                # Add delay before each request (except first)
                if attempt > 0:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                
                headers = self._get_headers(url)
                
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 403:
                        logger.warning(f"Access denied (403) for {url} - may be blocked by anti-bot measures")
                        # For 403 errors, wait longer before retry
                        if attempt < self.config.retry_attempts - 1:
                            await asyncio.sleep(random.uniform(5, 10))
                    elif response.status == 429:
                        logger.warning(f"Rate limited (429) for {url}")
                        # For rate limiting, wait even longer
                        if attempt < self.config.retry_attempts - 1:
                            await asyncio.sleep(random.uniform(10, 20))
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(base_delay * (2 ** attempt))
        
        logger.error(f"Failed to fetch {url} after {self.config.retry_attempts} attempts")
        return None
    
    def _extract_price(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[float]:
        """Extract price from HTML using CSS selectors."""
        for selector in selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    price_text = element.get_text(strip=True)
                    price = self._parse_price(price_text)
                    if price is not None:
                        return price
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price from text string."""
        if not price_text:
            return None
        
        # Remove common currency symbols and clean text
        price_text = re.sub(r'[^\d.,]+', '', price_text)
        price_text = price_text.replace(',', '')
        
        # Try to extract price as float
        try:
            return float(price_text)
        except (ValueError, TypeError):
            # Try to find price pattern
            price_match = re.search(r'(\d+\.?\d*)', price_text)
            if price_match:
                return float(price_match.group(1))
        
        return None
    
    def _extract_text(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract text from HTML using CSS selectors."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    return element.get_text(strip=True)
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        return None
    
    def _detect_site(self, url: str) -> Optional[str]:
        """Detect which site this URL belongs to."""
        domain = urlparse(url).netloc.lower()
        
        if 'amazon' in domain:
            return 'amazon'
        elif 'ebay' in domain:
            return 'ebay'
        elif 'walmart' in domain:
            return 'walmart'
        # Add more site detection logic here
        
        return None
    
    async def scrape_product_price(self, url: str, site_name: str = None) -> Dict[str, Any]:
        """Scrape price for a single product from a URL."""
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
            
            # Get site configuration
            site_config = self.config.get_site_config(site_name)
            if not site_config:
                result['error'] = f"No configuration found for site: {site_name}"
                return result
            
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
            
            # Extract price
            price_selectors = site_config.get('selectors', {}).get('price', [])
            price = self._extract_price(soup, price_selectors)
            
            if price is None:
                result['error'] = "Could not extract price from page"
                return result
            
            # Extract additional information
            title_selectors = site_config.get('selectors', {}).get('title', [])
            title = self._extract_text(soup, title_selectors)
            
            availability_selectors = site_config.get('selectors', {}).get('availability', [])
            availability_text = self._extract_text(soup, availability_selectors)
            availability = self._parse_availability(availability_text)
            
            result.update({
                'success': True,
                'price': price,
                'title': title,
                'availability': availability
            })
            
            logger.info(f"Successfully scraped {site_name}: ${price}")
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _parse_availability(self, availability_text: str) -> bool:
        """Parse availability from text."""
        if not availability_text:
            return True  # Assume available if no info
        
        availability_text = availability_text.lower()
        
        # Common out of stock indicators
        out_of_stock_indicators = [
            'out of stock', 'unavailable', 'sold out', 'not available',
            'temporarily out of stock', 'currently unavailable'
        ]
        
        for indicator in out_of_stock_indicators:
            if indicator in availability_text:
                return False
        
        return True


class ScraperManager:
    """Manages multiple price scrapers and coordinates scraping tasks."""
    
    def __init__(self, config: Config):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_requests)
    
    async def scrape_product(self, product: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Scrape prices for a single product across all configured sites."""
        product_id = product['id']
        urls = product['urls']
        
        results = {}
        
        async with PriceScraper(self.config) as scraper:
            tasks = []
            
            for site_name, url in urls.items():
                if self.config.is_site_enabled(site_name):
                    task = self._scrape_with_semaphore(scraper, url, site_name)
                    tasks.append((site_name, task))
                    
                    # Add delay between requests
                    await asyncio.sleep(self.config.delay_between_requests)
            
            # Wait for all tasks to complete
            for site_name, task in tasks:
                try:
                    result = await task
                    results[site_name] = result
                except Exception as e:
                    logger.error(f"Error scraping {site_name} for product {product_id}: {e}")
                    results[site_name] = {
                        'success': False,
                        'error': str(e)
                    }
        
        return results
    
    async def _scrape_with_semaphore(self, scraper: PriceScraper, url: str, site_name: str):
        """Scrape with semaphore to limit concurrent requests."""
        async with self.semaphore:
            return await scraper.scrape_product_price(url, site_name)
    
    async def scrape_all_products(self, products: List[Dict[str, Any]]) -> Dict[int, Dict[str, Dict[str, Any]]]:
        """Scrape prices for all products."""
        results = {}
        
        for product in products:
            try:
                product_id = product['id']
                logger.info(f"Scraping product: {product['name']} (ID: {product_id})")
                
                product_results = await self.scrape_product(product)
                results[product_id] = product_results
                
                # Add delay between products
                await asyncio.sleep(self.config.delay_between_requests)
                
            except Exception as e:
                logger.error(f"Error scraping product {product.get('id', 'unknown')}: {e}")
        
        return results
