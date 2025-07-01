"""
Database management for price tracking
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for price tracking."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    target_price REAL,
                    urls TEXT NOT NULL,  -- JSON string of site URLs
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    site_name TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT DEFAULT 'GBP',
                    availability BOOLEAN DEFAULT 1,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    site_name TEXT NOT NULL,
                    alert_price REAL NOT NULL,
                    triggered_at TIMESTAMP,
                    notified BOOLEAN DEFAULT 0,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_history_product_id 
                ON price_history (product_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_price_history_timestamp 
                ON price_history (timestamp)
            ''')
    
    def add_product(self, name: str, urls: Dict[str, str], 
                   description: str = None, target_price: float = None) -> int:
        """Add a new product to track."""
        urls_json = json.dumps(urls)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO products (name, description, target_price, urls)
                VALUES (?, ?, ?, ?)
            ''', (name, description, target_price, urls_json))
            
            product_id = cursor.lastrowid
            logger.info(f"Added product: {name} (ID: {product_id})")
            return product_id
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get product by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM products WHERE id = ? AND active = 1
            ''', (product_id,))
            
            row = cursor.fetchone()
            if row:
                product = dict(row)
                product['urls'] = json.loads(product['urls'])
                return product
            return None
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all active products."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM products WHERE active = 1 ORDER BY name
            ''')
            
            products = []
            for row in cursor.fetchall():
                product = dict(row)
                product['urls'] = json.loads(product['urls'])
                products.append(product)
            
            return products
    
    def update_product(self, product_id: int, **kwargs):
        """Update product information."""
        allowed_fields = ['name', 'description', 'target_price', 'urls']
        updates = []
        values = []
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'urls':
                    value = json.dumps(value)
                updates.append(f"{field} = ?")
                values.append(value)
        
        if not updates:
            return
        
        updates.append("updated_at = ?")
        values.append(datetime.now())
        values.append(product_id)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f'''
                UPDATE products SET {', '.join(updates)} WHERE id = ?
            ''', values)
    
    def deactivate_product(self, product_id: int):
        """Deactivate a product (soft delete)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE products SET active = 0, updated_at = ? WHERE id = ?
            ''', (datetime.now(), product_id))
    
    def delete_product(self, product_id: int):
        """Delete a product and all its associated price history."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete price history first (due to foreign key constraints)
            conn.execute('DELETE FROM price_history WHERE product_id = ?', (product_id,))
            
            # Delete the product
            conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    
    def save_price_history(self, product_id: int, site_name: str, price: float,
                          currency: str = 'GBP', availability: bool = True,
                          timestamp: datetime = None):
        """Save price history entry."""
        if timestamp is None:
            timestamp = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO price_history 
                (product_id, site_name, price, currency, availability, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (product_id, site_name, price, currency, availability, timestamp))
    
    def get_price_history(self, product_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get price history for a product."""
        start_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM price_history 
                WHERE product_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (product_id, start_date))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_latest_prices(self, product_id: int) -> Dict[str, Dict[str, Any]]:
        """Get latest price for each site for a product."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT DISTINCT site_name,
                       FIRST_VALUE(price) OVER (PARTITION BY site_name ORDER BY timestamp DESC) as price,
                       FIRST_VALUE(currency) OVER (PARTITION BY site_name ORDER BY timestamp DESC) as currency,
                       FIRST_VALUE(availability) OVER (PARTITION BY site_name ORDER BY timestamp DESC) as availability,
                       FIRST_VALUE(timestamp) OVER (PARTITION BY site_name ORDER BY timestamp DESC) as timestamp
                FROM price_history
                WHERE product_id = ?
            ''', (product_id,))
            
            result = {}
            for row in cursor.fetchall():
                result[row['site_name']] = {
                    'price': row['price'],
                    'currency': row['currency'],
                    'availability': bool(row['availability']),
                    'timestamp': row['timestamp']
                }
            
            return result
    
    def get_price_statistics(self, product_id: int, days: int = 30) -> Dict[str, Any]:
        """Get price statistics for a product."""
        start_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT site_name,
                       MIN(price) as min_price,
                       MAX(price) as max_price,
                       AVG(price) as avg_price,
                       COUNT(*) as data_points
                FROM price_history
                WHERE product_id = ? AND timestamp >= ?
                GROUP BY site_name
            ''', (product_id, start_date))
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    'min_price': row[1],
                    'max_price': row[2],
                    'avg_price': round(row[3], 2),
                    'data_points': row[4]
                }
            
            return stats
        
    def get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
