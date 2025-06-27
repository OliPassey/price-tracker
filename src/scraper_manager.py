"""
Scraper manager for coordinating price scraping tasks
"""

import asyncio
import logging
from typing import Dict, List, Any
from .scraper import ScraperManager as BaseScraper
from .uk_scraper import UKCateringScraper

logger = logging.getLogger(__name__)


class ScraperManager(BaseScraper):
    """Enhanced scraper manager with additional coordination features."""
    
    def __init__(self, config):
        super().__init__(config)
        self.active_tasks = {}
    
    async def scrape_product_by_id(self, product_id: int, product_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Scrape a specific product by ID with task tracking."""
        if product_id in self.active_tasks:
            logger.info(f"Product {product_id} is already being scraped")
            return await self.active_tasks[product_id]
        
        # Create and track the scraping task
        task = asyncio.create_task(self.scrape_product(product_data))
        self.active_tasks[product_id] = task
        
        try:
            result = await task
            return result
        finally:
            # Clean up completed task
            if product_id in self.active_tasks:
                del self.active_tasks[product_id]
    
    async def cancel_product_scraping(self, product_id: int) -> bool:
        """Cancel scraping for a specific product."""
        if product_id in self.active_tasks:
            task = self.active_tasks[product_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.active_tasks[product_id]
            logger.info(f"Cancelled scraping for product {product_id}")
            return True
        return False
    
    def get_active_scraping_tasks(self) -> List[int]:
        """Get list of product IDs currently being scraped."""
        return list(self.active_tasks.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the scraping system."""
        health_status = {
            'status': 'healthy',
            'active_tasks': len(self.active_tasks),
            'enabled_sites': len(self.config.get_enabled_sites()),
            'site_checks': {}
        }
        
        # Test each enabled site with a simple request
        enabled_sites = self.config.get_enabled_sites()
        
        for site_name in enabled_sites:
            site_config = self.config.get_site_config(site_name)
            base_url = site_config.get('base_url', '')
            
            try:
                from .scraper import PriceScraper
                async with PriceScraper(self.config) as scraper:
                    html_content = await scraper._fetch_page(base_url)
                    if html_content:
                        health_status['site_checks'][site_name] = 'accessible'
                    else:
                        health_status['site_checks'][site_name] = 'inaccessible'
            except Exception as e:
                health_status['site_checks'][site_name] = f'error: {str(e)}'
        
        # Determine overall health
        failed_sites = [site for site, status in health_status['site_checks'].items() 
                       if status != 'accessible']
        
        if len(failed_sites) == len(enabled_sites):
            health_status['status'] = 'unhealthy'
        elif failed_sites:
            health_status['status'] = 'degraded'
        
        return health_status
    
    async def scrape_product(self, product: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Scrape prices for a single product across all configured sites."""
        product_id = product['id']
        urls = product['urls']
        
        results = {}
        
        # Determine which scraper to use based on the sites
        uk_catering_sites = {'jjfoodservice', 'atoz_catering', 'amazon_uk'}
        has_uk_sites = any(site in uk_catering_sites for site in urls.keys())
        
        if has_uk_sites:
            # Use UK catering scraper
            async with UKCateringScraper(self.config) as scraper:
                tasks = []
                
                for site_name, url in urls.items():
                    if self.config.is_site_enabled(site_name):
                        task = self._scrape_with_semaphore_uk(scraper, url, site_name)
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
        else:
            # Use standard scraper for other sites
            results = await super().scrape_product(product)
        
        return results
    
    async def _scrape_with_semaphore_uk(self, scraper: UKCateringScraper, url: str, site_name: str):
        """Scrape with semaphore using UK scraper."""
        async with self.semaphore:
            return await scraper.scrape_product_price(url, site_name)
