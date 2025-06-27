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
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
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
