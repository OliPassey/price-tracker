# Price Tracker 🛒

A comprehensive web scraper for tracking product prices across multiple e-commerce sites. Built with Python, Beautiful Soup, and Flask.

## Features ✨

- **Multi-site Price Tracking**: Monitor prices across JJ Food Service, A to Z Catering, and Amazon UK
- **Beautiful Web UI**: Clean, responsive interface for managing products and viewing price history
- **Price Alerts**: Get notified when products reach your target price
- **Historical Data**: View price trends with interactive charts
- **Automated Scraping**: Schedule regular price checks
- **Multiple Notifications**: Email and webhook notifications
- **Robust Scraping**: Built-in retry logic, rotating user agents, and rate limiting
- **Special Pricing Detection**: Automatically detects and prioritizes delivery prices and special offers

## Quick Start 🚀

1. **Clone and Setup**:
   ```bash
   git clone <your-repo-url>
   cd price-tracker
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Start the Web UI**:
   ```bash
   source venv/bin/activate
   python main.py --mode web
   ```

3. **Visit**: http://localhost:5000

## Usage 📋

### Web Interface

The web interface provides:
- **Dashboard**: Overview of all tracked products with current prices
- **Add Products**: Easy form to add new products with URLs from multiple sites
- **Product Details**: Detailed view with price history charts and statistics
- **Settings**: Configuration management and system health checks

### Command Line

```bash
# Start web UI
python main.py --mode web

# Run scraping once
python main.py --mode scrape

# Add sample products for testing
python examples/add_sample_products.py

# Scheduled scraping (for cron jobs)
python scripts/scheduled_scraping.py
```

### Scheduled Scraping

Add to your crontab for automatic price checks:
```bash
# Every 6 hours
0 */6 * * * cd /path/to/price-tracker && source venv/bin/activate && python scripts/scheduled_scraping.py

# Daily at 8 AM
0 8 * * * cd /path/to/price-tracker && source venv/bin/activate && python scripts/scheduled_scraping.py
```

## Configuration ⚙️

Edit `config.json` to customize:

### Scraping Settings
```json
{
  "scraping": {
    "delay_between_requests": 2,
    "max_concurrent_requests": 5,
    "timeout": 30,
    "retry_attempts": 3
  }
}
```

### Email Notifications
```json
{
  "notifications": {
    "email": {
      "enabled": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "sender_email": "your-email@gmail.com",
      "sender_password": "your-app-password",
      "recipient_email": "alerts@yourdomain.com"
    }
  }
}
```

### Adding New Sites

Add new e-commerce sites by extending the sites configuration:

```json
{
  "sites": {
    "atoz_catering": {
      "enabled": true,
      "base_url": "https://www.atoz-catering.co.uk",
      "selectors": {
        "price": [
          ".my-price.price-offer",
          ".delivery-price",
          ".price"
        ],
        "special_offer": [
          ".my-price.price-offer",
          ".special-offer",
          "del:contains('£')"
        ]
      }
    }
  }
}
```

## Architecture 🏗️

- **`main.py`**: Application entry point
- **`src/config.py`**: Configuration management
- **`src/database.py`**: SQLite database operations
- **`src/scraper.py`**: Core scraping logic with Beautiful Soup
- **`src/scraper_manager.py`**: Scraping coordination and task management
- **`src/notification.py`**: Email and webhook notifications
- **`src/web_ui.py`**: Flask web interface
- **`templates/`**: HTML templates with Bootstrap styling

## Features in Detail 🔍

### Smart Price Extraction
- Multiple CSS selectors per site for robust price detection
- Handles various price formats and currencies  
- Availability detection (in stock/out of stock)
- Automatic retry with exponential backoff

### Data Storage
- SQLite database for price history
- Product management with URLs and target prices
- Price statistics and trend analysis

### Web Interface
- Responsive design with Bootstrap 5
- Interactive price charts with Plotly
- Real-time scraping from the UI
- Product comparison and best price highlighting

### Notifications
- Email alerts when target prices are reached
- Webhook integration for custom notifications
- Rich HTML email templates
- Test notification functionality

## Tips for Best Results 📈

1. **Respectful Scraping**: The tool includes delays and rate limiting to be respectful to websites
2. **URL Selection**: Use direct product page URLs, not search results or category pages
3. **Target Prices**: Set realistic target prices based on historical data
4. **Multiple Sites**: Track the same product on multiple sites for best deals
5. **Regular Updates**: Run scraping regularly but not too frequently (every few hours is good)

## Deployment 🚀

### Docker Deployment

1. **Build and run with Docker**:
   ```bash
   # Build the container
   docker build -t price-tracker .
   
   # Run with docker-compose
   docker-compose up -d
   ```

2. **Manual Docker deployment**:
   ```bash
   docker run -d \
     --name price-tracker \
     -p 5000:5000 \
     -v $(pwd)/data:/app/data \
     price-tracker
   ```

### CI/CD with Azure DevOps

The project includes Azure DevOps pipeline configuration for automated deployments:

1. **Setup GitHub Integration**:
   - See `AZURE-DEVOPS-SETUP.md` for detailed instructions
   - Pipeline pulls directly from GitHub
   - Automatic builds on push to `main` or `develop` branches

2. **Pipeline Features**:
   - Docker image build and push to registry
   - Security scanning with Trivy
   - Automated testing
   - Multi-environment deployment (dev/prod)

3. **Quick Setup**:
   ```bash
   # Update azure-pipelines.yml with your GitHub repo
   # Create GitHub service connection in Azure DevOps
   # Create Docker registry service connection
   # Run the pipeline
   ```

## Troubleshooting 🔧

### Common Issues

1. **No prices found**: Check if the CSS selectors are correct for the site
2. **403/429 errors**: Sites may be blocking requests - try different user agents or increase delays
3. **Database errors**: Ensure the database file is writable
4. **Email not working**: Verify SMTP settings and app passwords for Gmail

### Adding Debug Information

Enable debug logging by modifying the logging level in `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Legal and Ethical Considerations ⚖️

- Respect robots.txt files
- Don't overload servers with too many requests
- Use for personal/educational purposes
- Check terms of service for each site
- Be mindful of rate limits

## Contributing 🤝

Feel free to contribute by:
- Adding support for new e-commerce sites
- Improving CSS selectors for existing sites
- Adding new notification methods
- Enhancing the web UI
- Fixing bugs and improving performance

## License 📄

This project is for educational purposes. Please review the terms of service of websites you scrape and use responsibly.

---

**Happy price tracking! 🛍️**
