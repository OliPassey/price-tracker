"""
Configuration management for the price tracker
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Configuration manager for the price tracker application."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config.json"
        self._config = self._load_config()
        self._apply_env_overrides()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
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
