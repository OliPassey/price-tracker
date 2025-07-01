"""
Notification system for price alerts
"""

import smtplib
import logging
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manages notifications for price alerts."""
    
    def __init__(self, config):
        self.config = config
        self.notification_config = config.notification_config
    
    async def send_price_alerts(self, alerts: List[Dict[str, Any]]):
        """Send notifications for price alerts."""
        if not alerts:
            return
        
        # Send email notifications
        if self.notification_config.get('email', {}).get('enabled', False):
            await self._send_email_alerts(alerts)
        
        # Send webhook notifications
        if self.notification_config.get('webhook', {}).get('enabled', False):
            await self._send_webhook_alerts(alerts)
    
    async def _send_email_alerts(self, alerts: List[Dict[str, Any]]):
        """Send email notifications for price alerts."""
        email_config = self.notification_config.get('email', {})
        
        try:
            # Create email content
            subject = f"Price Alert: {len(alerts)} product(s) at target price!"
            body = self._create_email_body(alerts)
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config.get('sender_email')
            msg['To'] = email_config.get('recipient_email')
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            server = smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port'))
            server.starttls()
            # Use SMTP credentials from config (may be different from sender email)
            smtp_username = email_config.get('smtp_username') or email_config.get('sender_email')
            smtp_password = email_config.get('smtp_password') or email_config.get('sender_password')
            server.login(smtp_username, smtp_password)
            
            text = msg.as_string()
            server.sendmail(email_config.get('sender_email'), 
                          email_config.get('recipient_email'), text)
            server.quit()
            
            logger.info(f"Email alert sent for {len(alerts)} products")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    async def _send_webhook_alerts(self, alerts: List[Dict[str, Any]]):
        """Send webhook notifications for price alerts."""
        webhook_config = self.notification_config.get('webhook', {})
        webhook_url = webhook_config.get('url')
        
        if not webhook_url:
            return
        
        try:
            payload = {
                'timestamp': datetime.now().isoformat(),
                'alert_count': len(alerts),
                'alerts': []
            }
            
            for alert in alerts:
                payload['alerts'].append({
                    'product_name': alert['product']['name'],
                    'site': alert['site'],
                    'current_price': alert['current_price'],
                    'target_price': alert['target_price'],
                    'savings': alert['target_price'] - alert['current_price']
                })
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Webhook alert sent for {len(alerts)} products")
                    else:
                        logger.error(f"Webhook failed with status {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _create_email_body(self, alerts: List[Dict[str, Any]]) -> str:
        """Create HTML email body for price alerts."""
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
                .alert { border: 1px solid #ddd; margin: 10px 0; padding: 15px; background-color: #f9f9f9; }
                .product-name { font-size: 18px; font-weight: bold; color: #333; }
                .price-info { margin: 10px 0; }
                .current-price { color: #4CAF50; font-weight: bold; font-size: 16px; }
                .target-price { color: #666; }
                .savings { color: #FF5722; font-weight: bold; }
                .site { background-color: #2196F3; color: white; padding: 5px 10px; border-radius: 3px; font-size: 12px; }
                .footer { margin-top: 30px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Price Alert!</h1>
                <p>Great news! We found products at your target price!</p>
            </div>
        """
        
        for alert in alerts:
            product = alert['product']
            savings = alert['target_price'] - alert['current_price']
            
            html += f"""
            <div class="alert">
                <div class="product-name">{product['name']}</div>
                <div class="price-info">
                    <span class="site">{alert['site'].upper()}</span>
                    <br><br>
                    <span class="current-price">Current Price: £{alert['current_price']:.2f}</span><br>
                    <span class="target-price">Your Target: £{alert['target_price']:.2f}</span><br>
                    <span class="savings">You Save: £{savings:.2f}</span>
                </div>
            </div>
            """
        
        html += """
            <div class="footer">
                <p>This is an automated price alert from your Price Tracker system.</p>
                <p>Happy shopping! 🛒</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    async def send_test_notification(self) -> Dict[str, Any]:
        """Send a test notification to verify configuration."""
        test_result = {
            'email': {'enabled': False, 'success': False, 'error': None},
            'webhook': {'enabled': False, 'success': False, 'error': None}
        }
        
        # Test email
        if self.notification_config.get('email', {}).get('enabled', False):
            test_result['email']['enabled'] = True
            try:
                test_alerts = [{
                    'product': {'name': 'Test Product'},
                    'site': 'test-site',
                    'current_price': 19.99,
                    'target_price': 25.00
                }]
                await self._send_email_alerts(test_alerts)
                test_result['email']['success'] = True
            except Exception as e:
                test_result['email']['error'] = str(e)
        
        # Test webhook
        if self.notification_config.get('webhook', {}).get('enabled', False):
            test_result['webhook']['enabled'] = True
            try:
                test_alerts = [{
                    'product': {'name': 'Test Product'},
                    'site': 'test-site',
                    'current_price': 19.99,
                    'target_price': 25.00
                }]
                await self._send_webhook_alerts(test_alerts)
                test_result['webhook']['success'] = True
            except Exception as e:
                test_result['webhook']['error'] = str(e)
        
        return test_result
    
    def send_email(self, subject: str, message: str, html_message: str = None) -> bool:
        """Send a simple email notification (synchronous version)."""
        email_config = self.notification_config.get('email', {})
        
        if not email_config.get('enabled', False):
            logger.warning("Email notifications are disabled")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = email_config.get('sender_email')
            msg['To'] = email_config.get('recipient_email')
            msg['Subject'] = subject
            
            # Add text content
            if message:
                msg.attach(MIMEText(message, 'plain'))
            
            # Add HTML content if provided
            if html_message:
                msg.attach(MIMEText(html_message, 'html'))
            
            # Send email
            server = smtplib.SMTP(email_config.get('smtp_server'), email_config.get('smtp_port'))
            server.starttls()
            # Use SMTP credentials from config (may be different from sender email)
            smtp_username = email_config.get('smtp_username') or email_config.get('sender_email')
            smtp_password = email_config.get('smtp_password') or email_config.get('sender_password')
            server.login(smtp_username, smtp_password)
            
            text = msg.as_string()
            server.sendmail(email_config.get('sender_email'), 
                          email_config.get('recipient_email'), text)
            server.quit()
            
            logger.info(f"Email sent successfully: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
