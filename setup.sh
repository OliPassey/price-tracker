#!/bin/bash

# Price Tracker Setup Script
# This script helps set up the price tracker environment

echo "🛒 Price Tracker Setup"
echo "====================="

# Check if Python 3.8+ is installed
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $python_version"

if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
    echo "✓ Python version is suitable"
else
    echo "✗ Python 3.8+ is required"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Create initial database
echo ""
echo "🗄️  Initializing database..."
python3 -c "
from src.database import DatabaseManager
from src.config import Config
config = Config()
db = DatabaseManager(config.database_path)
print('Database initialized successfully!')
"

# Ask if user wants to add sample products
echo ""
read -p "Would you like to add sample products for testing? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏪 Adding sample products..."
    python3 examples/add_sample_products.py
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Configure settings in config.json if needed"
echo "3. Start the web UI: python main.py --mode web"
echo "4. Or run scraping: python main.py --mode scrape"
echo ""
echo "Web UI will be available at: http://localhost:5000"
echo ""
echo "For scheduled scraping, add this to your crontab:"
echo "0 */6 * * * cd $(pwd) && source venv/bin/activate && python scripts/scheduled_scraping.py"
