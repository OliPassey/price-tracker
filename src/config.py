"""
Configuration management for the price tracker
"""

import json
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


class Config:
    """Configuration manager for the price tracker application."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config.json"
        self._config_error = None
        self._config = self._load_config()
        self._apply_env_overrides()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return a minimal default configuration."""
        return {
            "database": {
                "path": "price_tracker.db"
            },
            "scraping": {
                "delay_between_requests": 2,
                "max_concurrent_requests": 1,
                "timeout": 30,
                "retry_attempts": 3,
                "user_agents": [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ]
            },
            "notifications": {
                "email": {
                    "enabled": False,
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_username": "",
                    "smtp_password": "",
                    "sender_email": "",
                    "sender_password": "",
                    "recipient_email": ""
                },
                "webhook": {
                    "enabled": False,
                    "url": ""
                }
            },
            "sites": {}
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with fallback to defaults."""
        config_file = Path(self.config_path)
        
        # Check if file exists
        if not config_file.exists():
            self._config_error = f"Configuration file not found: {self.config_path}"
            logging.warning(f"Config file not found: {self.config_path}. Using default configuration.")
            return self._get_default_config()
        
        # Try to load and parse the file
        try:
            with open(config_file, 'r') as f:
                content = f.read().strip()
                if not content:
                    self._config_error = f"Configuration file is empty: {self.config_path}"
                    logging.warning(f"Config file is empty: {self.config_path}. Using default configuration.")
                    return self._get_default_config()
                
                config = json.loads(content)
                if not isinstance(config, dict):
                    self._config_error = f"Configuration file must contain a JSON object: {self.config_path}"
                    logging.warning(f"Invalid config structure in {self.config_path}. Using default configuration.")
                    return self._get_default_config()
                
                return config
                
        except json.JSONDecodeError as e:
            self._config_error = f"Invalid JSON in configuration file {self.config_path}: {str(e)}"
            logging.warning(f"JSON parsing error in {self.config_path}: {str(e)}. Using default configuration.")
            return self._get_default_config()
        except Exception as e:
            self._config_error = f"Error reading configuration file {self.config_path}: {str(e)}"
            logging.warning(f"Error reading {self.config_path}: {str(e)}. Using default configuration.")
            return self._get_default_config()
    
    def has_config_error(self) -> bool:
        """Check if there was an error loading the configuration."""
        return self._config_error is not None
    
    def get_config_error(self) -> Optional[str]:
        """Get the configuration error message if any."""
        return self._config_error
    
    def create_default_config_file(self) -> bool:
        """Create a default configuration file."""
        try:
            default_config = {
                "database": {
                    "path": "price_tracker.db"
                },
                "scraping": {
                    "delay_between_requests": 2,
                    "max_concurrent_requests": 1,
                    "timeout": 30,
                    "retry_attempts": 3,
                    "special_pricing": {
                        "enabled": True,
                        "prefer_delivery_prices": True,
                        "detect_strikethrough": True,
                        "detect_was_now_patterns": True,
                        "detect_percentage_discounts": True,
                        "min_discount_threshold": 0.05,
                        "max_price_difference_ratio": 0.5
                    },
                    "user_agents": [
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    ]
                },
                "notifications": {
                    "email": {
                        "enabled": False,
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "smtp_username": "",
                        "smtp_password": "",
                        "sender_email": "",
                        "sender_password": "",
                        "recipient_email": ""
                    },
                    "webhook": {
                        "enabled": False,
                        "url": ""
                    }
                },
                "sites": {
                    "jjfoodservice": {
                        "enabled": True,
                        "base_url": "https://www.jjfoodservice.com",
                        "selectors": {
                            "price": [".price-delivery", ".delivery-price", ".price"],
                            "delivery_price": [".price-delivery", ".delivery-price"],
                            "special_offer": [".special-offer", ".sale-price", ".offer-price"],
                            "title": ["h1"],
                            "availability": [".stock-status", ".availability"]
                        }
                    },
                    "atoz_catering": {
                        "enabled": True,
                        "base_url": "https://www.atoz-catering.co.uk",
                        "selectors": {
                            "price": [".my-price.price-offer", ".delivery-price", ".price"],
                            "delivery_price": [".delivery-price", ".price-delivery"],
                            "special_offer": [".my-price.price-offer", ".special-offer", ".sale-price"],
                            "title": ["h1"],
                            "availability": [".stock-status", ".availability"]
                        }
                    },
                    "amazon_uk": {
                        "enabled": True,
                        "base_url": "https://www.amazon.co.uk",
                        "selectors": {
                            "price": [".a-price-whole", ".a-price .a-offscreen", "#priceblock_ourprice"],
                            "special_offer": ["#priceblock_dealprice", ".a-price-strike .a-offscreen", ".a-price-was"],
                            "title": ["#productTitle"],
                            "availability": ["#availability span"]
                        }
                    }
                }
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            
            logging.info(f"Created default configuration file: {self.config_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to create default config file: {str(e)}")
            return False
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Database path override
        if os.getenv('DATABASE_PATH'):
            if 'database' not in self._config:
                self._config['database'] = {}
            self._config['database']['path'] = os.getenv('DATABASE_PATH')
        
        # Email notification overrides
        email_env_vars = {
            'SMTP_SERVER': ['notifications', 'email', 'smtp_server'],
            'SMTP_PORT': ['notifications', 'email', 'smtp_port'],
            'SMTP_USERNAME': ['notifications', 'email', 'smtp_username'],
            'SMTP_PASSWORD': ['notifications', 'email', 'smtp_password'],
            'SENDER_EMAIL': ['notifications', 'email', 'sender_email'],
            'SENDER_PASSWORD': ['notifications', 'email', 'sender_password'],
            'RECIPIENT_EMAIL': ['notifications', 'email', 'recipient_email'],
            'EMAIL_ENABLED': ['notifications', 'email', 'enabled']
        }
        
        for env_var, config_path in email_env_vars.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._set_nested_config(config_path, env_value)
        
        # Webhook notification overrides
        webhook_env_vars = {
            'WEBHOOK_URL': ['notifications', 'webhook', 'url'],
            'WEBHOOK_ENABLED': ['notifications', 'webhook', 'enabled']
        }
        
        for env_var, config_path in webhook_env_vars.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._set_nested_config(config_path, env_value)
        
        # Scraping configuration overrides
        scraping_env_vars = {
            'DELAY_BETWEEN_REQUESTS': ['scraping', 'delay_between_requests'],
            'MAX_CONCURRENT_REQUESTS': ['scraping', 'max_concurrent_requests'],
            'REQUEST_TIMEOUT': ['scraping', 'timeout'],
            'RETRY_ATTEMPTS': ['scraping', 'retry_attempts']
        }
        
        for env_var, config_path in scraping_env_vars.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self._set_nested_config(config_path, env_value)
    
    def _set_nested_config(self, path: list, value: str):
        """Set a nested configuration value from environment variable."""
        # Convert string values to appropriate types
        converted_value = self._convert_env_value(value)
        
        # Navigate to the correct nested location
        current = self._config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[path[-1]] = converted_value
    
    def _convert_env_value(self, value: str):
        """Convert environment variable string to appropriate type."""
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle integer values
        if value.isdigit():
            return int(value)
        
        # Handle float values
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    @property
    def database_path(self) -> str:
        """Get database file path."""
        return self._config.get('database', {}).get('path', 'price_tracker.db')
    
    @property
    def scraping_config(self) -> Dict[str, Any]:
        """Get scraping configuration."""
        return self._config.get('scraping', {})
    
    @property
    def delay_between_requests(self) -> float:
        """Get delay between requests in seconds."""
        return self.scraping_config.get('delay_between_requests', 2)
    
    @property
    def max_concurrent_requests(self) -> int:
        """Get maximum concurrent requests."""
        return self.scraping_config.get('max_concurrent_requests', 5)
    
    @property
    def timeout(self) -> int:
        """Get request timeout in seconds."""
        return self.scraping_config.get('timeout', 30)
    
    @property
    def retry_attempts(self) -> int:
        """Get number of retry attempts."""
        return self.scraping_config.get('retry_attempts', 3)
    
    @property
    def user_agents(self) -> list:
        """Get list of user agents."""
        return self.scraping_config.get('user_agents', [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        ])
    
    @property
    def notification_config(self) -> Dict[str, Any]:
        """Get notification configuration."""
        return self._config.get('notifications', {})
    
    @property
    def sites_config(self) -> Dict[str, Any]:
        """Get sites configuration."""
        return self._config.get('sites', {})
    
    def get_site_config(self, site_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific site."""
        return self.sites_config.get(site_name)
    
    def is_site_enabled(self, site_name: str) -> bool:
        """Check if a site is enabled."""
        site_config = self.get_site_config(site_name)
        return site_config.get('enabled', False) if site_config else False
    
    def get_enabled_sites(self) -> list:
        """Get list of enabled sites."""
        return [site for site, config in self.sites_config.items() 
                if config.get('enabled', False)]
