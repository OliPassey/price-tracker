#!/usr/bin/env python3
"""
Test script to verify environment variable configuration overrides
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from config import Config

def test_env_overrides():
    """Test that environment variables properly override config.json settings."""
    
    # Create a temporary config file
    config_data = {
        "database": {"path": "default.db"},
        "scraping": {
            "delay_between_requests": 1,
            "max_concurrent_requests": 5,
            "timeout": 10,
            "retry_attempts": 1
        },
        "notifications": {
            "email": {
                "enabled": False,
                "smtp_server": "default.smtp.com",
                "smtp_port": 25,
                "sender_email": "default@example.com",
                "sender_password": "default_pass",
                "recipient_email": "default_recipient@example.com"
            },
            "webhook": {
                "enabled": False,
                "url": "http://default.webhook.com"
            }
        }
    }
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_config_path = f.name
    
    try:
        print("Testing environment variable overrides...")
        
        # Set environment variables
        os.environ['DATABASE_PATH'] = '/custom/database.db'
        os.environ['DELAY_BETWEEN_REQUESTS'] = '5'
        os.environ['MAX_CONCURRENT_REQUESTS'] = '10'
        os.environ['REQUEST_TIMEOUT'] = '60'
        os.environ['RETRY_ATTEMPTS'] = '5'
        os.environ['EMAIL_ENABLED'] = 'true'
        os.environ['SMTP_SERVER'] = 'custom.smtp.com'
        os.environ['SMTP_PORT'] = '587'
        os.environ['SENDER_EMAIL'] = 'custom@example.com'
        os.environ['SENDER_PASSWORD'] = 'custom_pass'
        os.environ['RECIPIENT_EMAIL'] = 'custom_recipient@example.com'
        os.environ['WEBHOOK_ENABLED'] = 'true'
        os.environ['WEBHOOK_URL'] = 'http://custom.webhook.com'
        
        # Load configuration
        config = Config(temp_config_path)
        
        # Test database path
        assert config.database_path == '/custom/database.db', f"Expected '/custom/database.db', got '{config.database_path}'"
        print("✓ Database path override works")
        
        # Test scraping config
        assert config.delay_between_requests == 5, f"Expected 5, got {config.delay_between_requests}"
        assert config.max_concurrent_requests == 10, f"Expected 10, got {config.max_concurrent_requests}"
        assert config.timeout == 60, f"Expected 60, got {config.timeout}"
        assert config.retry_attempts == 5, f"Expected 5, got {config.retry_attempts}"
        print("✓ Scraping configuration overrides work")
        
        # Test email config
        email_config = config.notification_config['email']
        assert email_config['enabled'] == True, f"Expected True, got {email_config['enabled']}"
        assert email_config['smtp_server'] == 'custom.smtp.com', f"Expected 'custom.smtp.com', got '{email_config['smtp_server']}'"
        assert email_config['smtp_port'] == 587, f"Expected 587, got {email_config['smtp_port']}"
        assert email_config['sender_email'] == 'custom@example.com', f"Expected 'custom@example.com', got '{email_config['sender_email']}'"
        assert email_config['sender_password'] == 'custom_pass', f"Expected 'custom_pass', got '{email_config['sender_password']}'"
        assert email_config['recipient_email'] == 'custom_recipient@example.com', f"Expected 'custom_recipient@example.com', got '{email_config['recipient_email']}'"
        print("✓ Email configuration overrides work")
        
        # Test webhook config
        webhook_config = config.notification_config['webhook']
        assert webhook_config['enabled'] == True, f"Expected True, got {webhook_config['enabled']}"
        assert webhook_config['url'] == 'http://custom.webhook.com', f"Expected 'http://custom.webhook.com', got '{webhook_config['url']}'"
        print("✓ Webhook configuration overrides work")
        
        print("\n🎉 All environment variable overrides are working correctly!")
        
    finally:
        # Clean up
        Path(temp_config_path).unlink()
        
        # Clean up environment variables
        env_vars = ['DATABASE_PATH', 'DELAY_BETWEEN_REQUESTS', 'MAX_CONCURRENT_REQUESTS', 
                   'REQUEST_TIMEOUT', 'RETRY_ATTEMPTS', 'EMAIL_ENABLED', 'SMTP_SERVER', 
                   'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD', 'RECIPIENT_EMAIL',
                   'WEBHOOK_ENABLED', 'WEBHOOK_URL']
        
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

if __name__ == '__main__':
    test_env_overrides()
