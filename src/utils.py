"""
Utility functions for the price tracker
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def format_price(price: float, currency: str = 'GBP') -> str:
    """Format price with appropriate currency symbol."""
    if currency == 'GBP':
        return f"£{price:.2f}"
    elif currency == 'USD':
        return f"${price:.2f}"
    elif currency == 'EUR':
        return f"€{price:.2f}"
    else:
        return f"{price:.2f} {currency}"


def calculate_price_change(old_price: float, new_price: float) -> Dict[str, Any]:
    """Calculate price change percentage and direction."""
    if old_price == 0:
        return {
            'change': 0.0,
            'percentage': 0.0,
            'direction': 'stable'
        }
    
    change = new_price - old_price
    percentage = (change / old_price) * 100
    
    if percentage > 0.1:
        direction = 'up'
    elif percentage < -0.1:
        direction = 'down'
    else:
        direction = 'stable'
    
    return {
        'change': change,
        'percentage': percentage,
        'direction': direction
    }


def is_site_accessible(site_name: str, last_success: datetime = None) -> bool:
    """Check if a site is likely accessible based on recent success."""
    if not last_success:
        return True  # Assume accessible if no data
    
    # Consider site inaccessible if no success in last 24 hours
    return (datetime.now() - last_success) < timedelta(hours=24)


def get_retry_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay with jitter."""
    import random
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # Add 10% jitter
    return delay + jitter


def clean_product_name(name: str) -> str:
    """Clean and normalize product name."""
    import re
    # Remove extra whitespace and normalize
    name = re.sub(r'\s+', ' ', name.strip())
    # Remove special characters that might cause issues
    name = re.sub(r'[^\w\s\-\(\)&]', '', name)
    return name


def is_valid_price(price: float) -> bool:
    """Check if a price is valid (positive and reasonable)."""
    return price > 0 and price < 10000  # Max £10,000 seems reasonable for catering supplies


def get_price_alert_message(product_name: str, site_name: str, current_price: float, 
                           target_price: float, currency: str = 'GBP') -> str:
    """Generate price alert message."""
    current_formatted = format_price(current_price, currency)
    target_formatted = format_price(target_price, currency)
    
    return (f"Price Alert: {product_name} is now {current_formatted} on {site_name}, "
            f"which is at or below your target price of {target_formatted}!")


def group_results_by_status(results: Dict[str, Dict[str, Any]]) -> Dict[str, List]:
    """Group scraping results by success/failure status."""
    grouped = {
        'successful': [],
        'failed': [],
        'blocked': []
    }
    
    for site_name, result in results.items():
        if result.get('success'):
            grouped['successful'].append({
                'site': site_name,
                'price': result.get('price'),
                'currency': result.get('currency', 'GBP')
            })
        elif 'blocked' in str(result.get('error', '')).lower() or '403' in str(result.get('error', '')):
            grouped['blocked'].append({
                'site': site_name,
                'error': result.get('error')
            })
        else:
            grouped['failed'].append({
                'site': site_name,
                'error': result.get('error')
            })
    
    return grouped
