"""
Automated shopping list generator for price tracker
Analyzes scraped prices to determine cheapest store for each product
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

from .database import DatabaseManager
from .notification import NotificationManager

logger = logging.getLogger(__name__)


@dataclass
class ShoppingItem:
    """Represents an item in a shopping list."""
    product_id: int
    product_name: str
    current_price: float
    store_name: str
    store_url: str
    last_updated: datetime
    savings_vs_most_expensive: float = 0.0


@dataclass
class StoreShoppingList:
    """Represents a complete shopping list for one store."""
    store_name: str
    store_display_name: str
    base_url: str
    items: List[ShoppingItem]
    total_cost: float
    total_savings: float
    item_count: int


class AutoShoppingListGenerator:
    """Generates automated shopping lists based on current best prices."""
    
    def __init__(self, db_manager: DatabaseManager, notification_manager: NotificationManager = None):
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        
        # Store display names and URLs
        self.store_info = {
            'jjfoodservice': {
                'display_name': 'JJ Food Service',
                'base_url': 'https://www.jjfoodservice.com'
            },
            'atoz_catering': {
                'display_name': 'A to Z Catering', 
                'base_url': 'https://www.atoz-catering.co.uk'
            },
            'amazon_uk': {
                'display_name': 'Amazon UK',
                'base_url': 'https://www.amazon.co.uk'
            }
        }
    
    def get_current_best_prices(self) -> Dict[int, Dict]:
        """Get the current cheapest price for each product across all stores."""
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        
        # Get latest price for each product from each store
        query = """
        WITH latest_prices AS (
            SELECT 
                p.id as product_id,
                p.name as product_name,
                ph.site_name,
                ph.price,
                ph.timestamp,
                p.urls,
                ROW_NUMBER() OVER (PARTITION BY p.id, ph.site_name ORDER BY ph.timestamp DESC) as rn
            FROM products p
            LEFT JOIN price_history ph ON p.id = ph.product_id
            WHERE ph.price IS NOT NULL AND ph.price > 0 AND p.active = 1
        ),
        current_prices AS (
            SELECT * FROM latest_prices WHERE rn = 1
        ),
        cheapest_per_product AS (
            SELECT 
                product_id,
                product_name,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM current_prices
            GROUP BY product_id, product_name
        )
        SELECT 
            cp.product_id,
            cp.product_name,
            cp.site_name,
            cp.price,
            cp.timestamp,
            cp.urls,
            cpp.min_price,
            cpp.max_price
        FROM current_prices cp
        JOIN cheapest_per_product cpp ON cp.product_id = cpp.product_id
        WHERE cp.price = cpp.min_price
        ORDER BY cp.product_name, cp.site_name
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        # Group by product (handle ties where multiple stores have same lowest price)
        best_prices = {}
        for row in results:
            product_id = row[0]
            if product_id not in best_prices:
                best_prices[product_id] = []
            
            # Parse URLs from JSON
            urls = json.loads(row[5]) if row[5] else {}
            site_name = row[2]
            store_url = urls.get(site_name, "")
            
            best_prices[product_id].append({
                'product_name': row[1],
                'store_name': site_name,
                'price': row[3],
                'scraped_at': datetime.fromisoformat(row[4]),
                'store_url': store_url,
                'min_price': row[6],
                'max_price': row[7]
            })
        
        return best_prices
    
    def generate_shopping_lists(self) -> List[StoreShoppingList]:
        """Generate automated shopping lists for each store."""
        best_prices = self.get_current_best_prices()
        
        # Group items by store
        store_lists = {}
        
        for product_id, price_options in best_prices.items():
            # If multiple stores have the same lowest price, prefer in order: JJ Food Service, A to Z, Amazon
            store_priority = {'jjfoodservice': 1, 'atoz_catering': 2, 'amazon_uk': 3}
            best_option = min(price_options, key=lambda x: (x['price'], store_priority.get(x['store_name'], 999)))
            
            store_name = best_option['store_name']
            if store_name not in store_lists:
                store_lists[store_name] = []
            
            # Calculate savings vs most expensive option
            savings = best_option['max_price'] - best_option['price']
            
            shopping_item = ShoppingItem(
                product_id=product_id,
                product_name=best_option['product_name'],
                current_price=best_option['price'],
                store_name=store_name,
                store_url=best_option['store_url'],
                last_updated=best_option['scraped_at'],
                savings_vs_most_expensive=savings
            )
            
            store_lists[store_name].append(shopping_item)
        
        # Convert to StoreShoppingList objects
        shopping_lists = []
        for store_name, items in store_lists.items():
            store_info = self.store_info.get(store_name, {
                'display_name': store_name.title(),
                'base_url': ''
            })
            
            total_cost = sum(item.current_price for item in items)
            total_savings = sum(item.savings_vs_most_expensive for item in items)
            
            shopping_list = StoreShoppingList(
                store_name=store_name,
                store_display_name=store_info['display_name'],
                base_url=store_info['base_url'],
                items=sorted(items, key=lambda x: x.product_name.lower()),
                total_cost=total_cost,
                total_savings=total_savings,
                item_count=len(items)
            )
            
            shopping_lists.append(shopping_list)
        
        # Sort by total cost (cheapest store first)
        return sorted(shopping_lists, key=lambda x: x.total_cost)
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics about the current shopping recommendations."""
        shopping_lists = self.generate_shopping_lists()
        
        total_products = sum(sl.item_count for sl in shopping_lists)
        total_cost = sum(sl.total_cost for sl in shopping_lists)
        total_savings = sum(sl.total_savings for sl in shopping_lists)
        
        # Find the most recommended store
        best_store = max(shopping_lists, key=lambda x: x.item_count) if shopping_lists else None
        
        return {
            'total_products': total_products,
            'total_cost': total_cost,
            'total_savings': total_savings,
            'store_count': len(shopping_lists),
            'most_items_store': best_store.store_display_name if best_store else None,
            'most_items_count': best_store.item_count if best_store else 0,
            'generated_at': datetime.now()
        }
    
    def send_daily_shopping_list(self) -> bool:
        """Send daily shopping list via email/webhook."""
        if not self.notification_manager:
            return False
        
        try:
            shopping_lists = self.generate_shopping_lists()
            summary = self.get_summary_stats()
            
            if not shopping_lists:
                return False
            
            # Generate email content
            subject = f"Daily Shopping List - £{summary['total_cost']:.2f} across {summary['store_count']} stores"
            
            html_content = self._generate_email_html(shopping_lists, summary)
            text_content = self._generate_email_text(shopping_lists, summary)
            
            # Send email notification
            success = self.notification_manager.send_email(
                subject=subject,
                message=text_content,
                html_message=html_content
            )
            
            # Send webhook if configured
            if self.notification_manager.config.get('webhook', {}).get('enabled'):
                webhook_data = {
                    'type': 'daily_shopping_list',
                    'summary': summary,
                    'store_lists': [
                        {
                            'store': sl.store_display_name,
                            'items': len(sl.items),
                            'total': sl.total_cost,
                            'savings': sl.total_savings
                        }
                        for sl in shopping_lists
                    ]
                }
                self.notification_manager.send_webhook(webhook_data)
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily shopping list: {str(e)}")
            return False
    
    def _generate_email_html(self, shopping_lists: List[StoreShoppingList], summary: Dict) -> str:
        """Generate HTML email content for shopping lists."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #007bff; color: white; padding: 20px; border-radius: 5px; text-align: center; }}
                .summary {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .store-section {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
                .store-header {{ background: #28a745; color: white; padding: 15px; }}
                .item-list {{ padding: 0; margin: 0; list-style: none; }}
                .item {{ padding: 10px 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; }}
                .item:last-child {{ border-bottom: none; }}
                .price {{ font-weight: bold; color: #28a745; }}
                .savings {{ color: #dc3545; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛒 Daily Shopping List</h1>
                    <p>Best prices found for {summary['generated_at'].strftime('%B %d, %Y')}</p>
                </div>
                
                <div class="summary">
                    <h3>Summary</h3>
                    <ul>
                        <li><strong>{summary['total_products']}</strong> products tracked</li>
                        <li><strong>£{summary['total_cost']:.2f}</strong> total cost at best prices</li>
                        <li><strong>£{summary['total_savings']:.2f}</strong> total savings vs most expensive options</li>
                        <li><strong>{summary['store_count']}</strong> stores recommended</li>
                    </ul>
                </div>
        """
        
        for store_list in shopping_lists:
            html += f"""
                <div class="store-section">
                    <div class="store-header">
                        <h3>{store_list.store_display_name}</h3>
                        <p>{store_list.item_count} items - £{store_list.total_cost:.2f} total (Save £{store_list.total_savings:.2f})</p>
                    </div>
                    <ul class="item-list">
            """
            
            for item in store_list.items:
                savings_text = f"(Save £{item.savings_vs_most_expensive:.2f})" if item.savings_vs_most_expensive > 0 else ""
                url_link = f'<a href="{item.store_url}" target="_blank">🔗</a>' if item.store_url else ""
                
                html += f"""
                        <li class="item">
                            <span>{item.product_name} {url_link}</span>
                            <span>
                                <span class="price">£{item.current_price:.2f}</span>
                                <span class="savings">{savings_text}</span>
                            </span>
                        </li>
                """
            
            html += """
                    </ul>
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_email_text(self, shopping_lists: List[StoreShoppingList], summary: Dict) -> str:
        """Generate plain text email content for shopping lists."""
        text = f"""
DAILY SHOPPING LIST - {summary['generated_at'].strftime('%B %d, %Y')}
{'=' * 50}

SUMMARY:
- {summary['total_products']} products tracked
- £{summary['total_cost']:.2f} total cost at best prices  
- £{summary['total_savings']:.2f} total savings vs most expensive options
- {summary['store_count']} stores recommended

"""
        
        for store_list in shopping_lists:
            text += f"""
{store_list.store_display_name.upper()}
{'-' * len(store_list.store_display_name)}
{store_list.item_count} items - £{store_list.total_cost:.2f} total (Save £{store_list.total_savings:.2f})

"""
            
            for item in store_list.items:
                savings_text = f" (Save £{item.savings_vs_most_expensive:.2f})" if item.savings_vs_most_expensive > 0 else ""
                text += f"• {item.product_name}: £{item.current_price:.2f}{savings_text}\n"
            
            text += "\n"
        
        return text
    
    def _init_shopping_list_tables(self):
        """Initialize shopping list related database tables."""
        with self.db.get_connection() as conn:
            # Table to store generated shopping lists
            conn.execute('''
                CREATE TABLE IF NOT EXISTS shopping_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_name TEXT NOT NULL,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_cost REAL NOT NULL,
                    total_savings REAL DEFAULT 0,
                    item_count INTEGER NOT NULL,
                    list_data TEXT NOT NULL,  -- JSON string of the full list
                    sent_at TIMESTAMP,
                    email_sent BOOLEAN DEFAULT 0,
                    webhook_sent BOOLEAN DEFAULT 0
                )
            ''')
            
            # Table to track user preferences for shopping lists
            conn.execute('''
                CREATE TABLE IF NOT EXISTS shopping_list_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_name TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN DEFAULT 1,
                    min_savings_threshold REAL DEFAULT 0,
                    max_items INTEGER DEFAULT 50,
                    include_out_of_stock BOOLEAN DEFAULT 0,
                    auto_send_email BOOLEAN DEFAULT 1,
                    auto_send_webhook BOOLEAN DEFAULT 0,
                    send_time TEXT DEFAULT '09:00',  -- HH:MM format
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def get_latest_prices_by_store(self, days_back: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Get the latest prices for all products grouped by store."""
        with self.db.get_connection() as conn:
            query = '''
                SELECT 
                    p.id as product_id,
                    p.name as product_name,
                    p.description,
                    p.target_price,
                    p.urls,
                    ph.site_name,
                    ph.price,
                    ph.availability,
                    ph.timestamp
                FROM products p
                JOIN price_history ph ON p.id = ph.product_id
                WHERE p.active = 1 
                AND ph.timestamp >= datetime('now', '-{} days')
                AND ph.id IN (
                    SELECT MAX(id) 
                    FROM price_history ph2 
                    WHERE ph2.product_id = p.id 
                    AND ph2.site_name = ph.site_name
                    GROUP BY ph2.product_id, ph2.site_name
                )
                ORDER BY ph.site_name, p.name
            '''.format(days_back)
            
            cursor = conn.execute(query)
            results = cursor.fetchall()
            
            # Group by store
            stores = {}
            for row in results:
                product_id, name, desc, target, urls_json, site, price, avail, timestamp = row
                
                if site not in stores:
                    stores[site] = []
                
                # Parse URLs to get the specific URL for this site
                try:
                    urls = json.loads(urls_json) if urls_json else {}
                    site_url = urls.get(site, '')
                except:
                    site_url = ''
                
                stores[site].append({
                    'product_id': product_id,
                    'name': name,
                    'description': desc or '',
                    'target_price': target,
                    'price': price,
                    'availability': bool(avail),
                    'timestamp': timestamp,
                    'url': site_url
                })
            
            return stores
    
    def generate_shopping_list_for_store(self, store_name: str, preferences: Optional[Dict] = None) -> StoreShoppingList:
        """Generate a shopping list for a specific store with the best prices."""
        if preferences is None:
            preferences = self.get_store_preferences(store_name)
        
        # Get latest prices
        all_stores = self.get_latest_prices_by_store()
        store_items = all_stores.get(store_name, [])
        
        shopping_items = []
        total_cost = 0.0
        total_savings = 0.0
        
        for item in store_items:
            # Skip out of stock items if preference is set
            if not preferences.get('include_out_of_stock', False) and not item['availability']:
                continue
            
            # Calculate savings if target price is set
            savings = 0.0
            if item['target_price'] and item['price'] < item['target_price']:
                savings = item['target_price'] - item['price']
            
            # Skip items below savings threshold
            min_threshold = preferences.get('min_savings_threshold', 0)
            if min_threshold > 0 and savings < min_threshold:
                continue
            
            shopping_item = ShoppingItem(
                product_id=item['product_id'],
                product_name=item['name'],
                current_price=item['price'],
                store_name=store_name,
                store_url=item['url'],
                last_updated=datetime.fromisoformat(item['timestamp'].replace('Z', '+00:00')) if isinstance(item['timestamp'], str) else datetime.now(),
                savings_vs_most_expensive=savings
            )
            
            shopping_items.append(shopping_item)
            total_cost += item['price']
            total_savings += savings
        
        # Limit items if max_items is set
        max_items = preferences.get('max_items', 50)
        if len(shopping_items) > max_items:
            # Sort by savings (highest first) and take top items
            shopping_items.sort(key=lambda x: x.savings or 0, reverse=True)
            shopping_items = shopping_items[:max_items]
            total_cost = sum(item.best_price for item in shopping_items)
            total_savings = sum(item.savings or 0 for item in shopping_items)
        
        return StoreShoppingList(
            store_name=store_name,
            store_display_name=self.store_info.get(store_name, {}).get('display_name', store_name.title()),
            base_url=self.store_info.get(store_name, {}).get('base_url', ''),
            items=shopping_items,
            total_cost=total_cost,
            total_savings=total_savings,
            item_count=len(shopping_items)
        )
    
    def generate_all_shopping_lists(self) -> Dict[str, StoreShoppingList]:
        """Generate shopping lists for all enabled stores."""
        enabled_stores = self.get_enabled_stores()
        shopping_lists = {}
        
        for store_name in enabled_stores:
            try:
                shopping_list = self.generate_shopping_list_for_store(store_name)
                if shopping_list.items:  # Only include lists with items
                    shopping_lists[store_name] = shopping_list
                    logger.info(f"Generated shopping list for {store_name} with {len(shopping_list.items)} items")
            except Exception as e:
                logger.error(f"Failed to generate shopping list for {store_name}: {str(e)}")
        
        return shopping_lists
    
    def save_shopping_list(self, shopping_list: StoreShoppingList) -> int:
        """Save a shopping list to the database."""
        import json
        
        with self.db.get_connection() as conn:
            # Convert shopping list to JSON for storage
            list_data = {
                'store_name': shopping_list.store_name,
                'items': [
                    {
                        'product_id': item.product_id,
                        'product_name': item.product_name,
                        'description': item.description,
                        'best_price': item.best_price,
                        'site_name': item.site_name,
                        'url': item.url,
                        'availability': item.availability,
                        'last_updated': item.last_updated.isoformat(),
                        'target_price': item.target_price,
                        'savings': item.savings
                    }
                    for item in shopping_list.items
                ],
                'total_cost': shopping_list.total_cost,
                'total_savings': shopping_list.total_savings,
                'generated_at': shopping_list.generated_at.isoformat(),
                'item_count': shopping_list.item_count
            }
            
            cursor = conn.execute('''
                INSERT INTO shopping_lists 
                (store_name, total_cost, total_savings, item_count, list_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                shopping_list.store_name,
                shopping_list.total_cost,
                shopping_list.total_savings,
                shopping_list.item_count,
                json.dumps(list_data)
            ))
            
            return cursor.lastrowid
    
    def get_store_preferences(self, store_name: str) -> Dict[str, Any]:
        """Get preferences for a specific store."""
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT enabled, min_savings_threshold, max_items, include_out_of_stock,
                       auto_send_email, auto_send_webhook, send_time
                FROM shopping_list_preferences
                WHERE store_name = ?
            ''', (store_name,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'enabled': bool(row[0]),
                    'min_savings_threshold': row[1],
                    'max_items': row[2],
                    'include_out_of_stock': bool(row[3]),
                    'auto_send_email': bool(row[4]),
                    'auto_send_webhook': bool(row[5]),
                    'send_time': row[6]
                }
            else:
                # Return default preferences
                return {
                    'enabled': True,
                    'min_savings_threshold': 0.0,
                    'max_items': 50,
                    'include_out_of_stock': False,
                    'auto_send_email': True,
                    'auto_send_webhook': False,
                    'send_time': '09:00'
                }
    
    def get_enabled_stores(self) -> List[str]:
        """Get list of stores that have shopping lists enabled."""
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT DISTINCT store_name 
                FROM shopping_list_preferences 
                WHERE enabled = 1
            ''')
            enabled_stores = [row[0] for row in cursor.fetchall()]
            
            # If no preferences set, return all stores that have recent price data
            if not enabled_stores:
                cursor = conn.execute('''
                    SELECT DISTINCT site_name 
                    FROM price_history 
                    WHERE timestamp >= datetime('now', '-7 days')
                ''')
                enabled_stores = [row[0] for row in cursor.fetchall()]
            
            return enabled_stores
    
    def update_store_preferences(self, store_name: str, preferences: Dict[str, Any]) -> bool:
        """Update preferences for a specific store."""
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO shopping_list_preferences 
                (store_name, enabled, min_savings_threshold, max_items, include_out_of_stock,
                 auto_send_email, auto_send_webhook, send_time, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                store_name,
                preferences.get('enabled', True),
                preferences.get('min_savings_threshold', 0.0),
                preferences.get('max_items', 50),
                preferences.get('include_out_of_stock', False),
                preferences.get('auto_send_email', True),
                preferences.get('auto_send_webhook', False),
                preferences.get('send_time', '09:00')
            ))
            
            return True
    
    async def send_shopping_lists(self, shopping_lists: Dict[str, StoreShoppingList]) -> Dict[str, bool]:
        """Send shopping lists via email and/or webhook."""
        results = {}
        
        for store_name, shopping_list in shopping_lists.items():
            preferences = self.get_store_preferences(store_name)
            sent = False
            
            try:
                # Generate email content
                if preferences.get('auto_send_email', True):
                    email_content = self._generate_email_content(shopping_list)
                    email_sent = await self.notification_manager.send_email(
                        subject=f"Daily Shopping List - {store_name}",
                        body=email_content,
                        html_body=self._generate_html_email_content(shopping_list)
                    )
                    sent = sent or email_sent
                
                # Send webhook
                if preferences.get('auto_send_webhook', False):
                    webhook_data = self._generate_webhook_data(shopping_list)
                    webhook_sent = await self.notification_manager.send_webhook(webhook_data)
                    sent = sent or webhook_sent
                
                # Update database with send status
                if sent:
                    list_id = self.save_shopping_list(shopping_list)
                    with self.db.get_connection() as conn:
                        conn.execute('''
                            UPDATE shopping_lists 
                            SET sent_at = CURRENT_TIMESTAMP,
                                email_sent = ?, webhook_sent = ?
                            WHERE id = ?
                        ''', (
                            preferences.get('auto_send_email', True),
                            preferences.get('auto_send_webhook', False),
                            list_id
                        ))
                
                results[store_name] = sent
                
            except Exception as e:
                logger.error(f"Failed to send shopping list for {store_name}: {str(e)}")
                results[store_name] = False
        
        return results
    
    def _generate_email_content(self, shopping_list: StoreShoppingList) -> str:
        """Generate plain text email content for shopping list."""
        content = f"""
Daily Shopping List - {shopping_list.store_name}
Generated: {shopping_list.generated_at.strftime('%Y-%m-%d %H:%M')}

Summary:
- Items: {shopping_list.item_count}
- Total Cost: £{shopping_list.total_cost:.2f}
- Total Savings: £{shopping_list.total_savings:.2f}

Items:
"""
        
        for item in shopping_list.items:
            content += f"\n• {item.product_name}"
            content += f"\n  Price: £{item.best_price:.2f}"
            if item.target_price:
                content += f" (Target: £{item.target_price:.2f})"
            if item.savings:
                content += f" - Save £{item.savings:.2f}!"
            if not item.availability:
                content += " [OUT OF STOCK]"
            if item.url:
                content += f"\n  Link: {item.url}"
            content += "\n"
        
        content += f"\n\nHappy shopping!\n"
        return content
    
    def _generate_html_email_content(self, shopping_list: StoreShoppingList) -> str:
        """Generate HTML email content for shopping list."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .summary {{ background-color: #e3f2fd; padding: 15px; border-radius: 6px; margin-bottom: 20px; }}
        .item {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; border-radius: 6px; }}
        .item.out-of-stock {{ background-color: #ffebee; }}
        .price {{ font-size: 18px; font-weight: bold; color: #2e7d32; }}
        .savings {{ color: #d32f2f; font-weight: bold; }}
        .total {{ font-size: 20px; font-weight: bold; margin-top: 20px; }}
        a {{ color: #1976d2; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Daily Shopping List - {shopping_list.store_name}</h1>
        <p>Generated: {shopping_list.generated_at.strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    
    <div class="summary">
        <h3>Summary</h3>
        <p><strong>Items:</strong> {shopping_list.item_count}</p>
        <p><strong>Total Cost:</strong> £{shopping_list.total_cost:.2f}</p>
        <p><strong>Total Savings:</strong> <span class="savings">£{shopping_list.total_savings:.2f}</span></p>
    </div>
    
    <h3>Items</h3>
"""
        
        for item in shopping_list.items:
            availability_class = "" if item.availability else "out-of-stock"
            html += f'<div class="item {availability_class}">'
            html += f'<h4>{item.product_name}</h4>'
            if item.description:
                html += f'<p>{item.description}</p>'
            
            html += f'<div class="price">£{item.best_price:.2f}</div>'
            
            if item.target_price:
                html += f'<p>Target Price: £{item.target_price:.2f}</p>'
            
            if item.savings:
                html += f'<p class="savings">Save £{item.savings:.2f}!</p>'
            
            if not item.availability:
                html += '<p style="color: red;"><strong>OUT OF STOCK</strong></p>'
            
            if item.url:
                html += f'<p><a href="{item.url}" target="_blank">View Product</a></p>'
            
            html += '</div>'
        
        html += f"""
    <div class="total">
        <p>Total Shopping Cost: £{shopping_list.total_cost:.2f}</p>
        <p>Total Savings: <span class="savings">£{shopping_list.total_savings:.2f}</span></p>
    </div>
    
    <p>Happy shopping!</p>
</body>
</html>
"""
        return html
    
    def _generate_webhook_data(self, shopping_list: StoreShoppingList) -> Dict[str, Any]:
        """Generate webhook data for shopping list."""
        return {
            "type": "daily_shopping_list",
            "store_name": shopping_list.store_name,
            "generated_at": shopping_list.generated_at.isoformat(),
            "summary": {
                "item_count": shopping_list.item_count,
                "total_cost": shopping_list.total_cost,
                "total_savings": shopping_list.total_savings
            },
            "items": [
                {
                    "product_id": item.product_id,
                    "name": item.product_name,
                    "price": item.best_price,
                    "savings": item.savings,
                    "availability": item.availability,
                    "url": item.url
                }
                for item in shopping_list.items
            ]
        }
