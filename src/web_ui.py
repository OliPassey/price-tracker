"""
Web UI for the price tracker application
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_from_directory
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, TextAreaField, SubmitField, URLField
from wtforms.validators import DataRequired, NumberRange, URL, Optional
import json
import asyncio
from datetime import datetime, timedelta
import plotly
import plotly.graph_objs as go
import pandas as pd
import os

from .database import DatabaseManager
from .config import Config
from .scraper_manager import ScraperManager
from .notification import NotificationManager
from .utils import format_price, group_results_by_status


def create_app():
    """Create Flask application."""
    # Get the project root directory (parent of src)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    
    app = Flask(__name__, template_folder=template_dir)
    app.config['SECRET_KEY'] = 'your-secret-key-change-this'
    
    # Initialize components
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    scraper_manager = ScraperManager(config)
    notification_manager = NotificationManager(config)
    
    class ProductForm(FlaskForm):
        name = StringField('Product Name', validators=[DataRequired()])
        description = TextAreaField('Description')
        target_price = FloatField('Target Price (£)', validators=[Optional(), NumberRange(min=0)])
        jjfoodservice_url = URLField('JJ Food Service URL', validators=[Optional(), URL()])
        atoz_catering_url = URLField('A to Z Catering URL', validators=[Optional(), URL()])
        amazon_uk_url = URLField('Amazon UK URL', validators=[Optional(), URL()])
        submit = SubmitField('Add Product')
    
    @app.route('/')
    def index():
        """Home page showing all products."""
        products = db_manager.get_all_products()
        
        # Get latest prices for each product
        for product in products:
            latest_prices = db_manager.get_latest_prices(product['id'])
            product['latest_prices'] = latest_prices
            
            # Find best current price
            if latest_prices:
                best_price = min(latest_prices.values(), key=lambda x: x['price'])
                product['best_price'] = best_price
            else:
                product['best_price'] = None
        
        return render_template('index.html', products=products)
    
    @app.route('/add_product', methods=['GET', 'POST'])
    def add_product():
        """Add a new product to track."""
        form = ProductForm()
        
        if form.validate_on_submit():
            urls = {}
            if form.jjfoodservice_url.data:
                urls['jjfoodservice'] = form.jjfoodservice_url.data
            if form.atoz_catering_url.data:
                urls['atoz_catering'] = form.atoz_catering_url.data
            if form.amazon_uk_url.data:
                urls['amazon_uk'] = form.amazon_uk_url.data
            
            if not urls:
                flash('Please provide at least one URL to track.', 'error')
                return render_template('add_product.html', form=form)
            
            try:
                product_id = db_manager.add_product(
                    name=form.name.data,
                    description=form.description.data,
                    target_price=form.target_price.data,
                    urls=urls
                )
                flash(f'Product "{form.name.data}" added successfully!', 'success')
                return redirect(url_for('product_detail', product_id=product_id))
            except Exception as e:
                flash(f'Error adding product: {str(e)}', 'error')
        
        return render_template('add_product.html', form=form)
    
    @app.route('/product/<int:product_id>')
    def product_detail(product_id):
        """Show detailed information for a product."""
        product = db_manager.get_product(product_id)
        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))
        
        # Get price history
        price_history = db_manager.get_price_history(product_id, days=30)
        latest_prices = db_manager.get_latest_prices(product_id)
        price_stats = db_manager.get_price_statistics(product_id, days=30)
        
        # Create price chart
        chart_json = create_price_chart(price_history, product['name'])
        
        return render_template('product_detail.html', 
                             product=product,
                             price_history=price_history,
                             latest_prices=latest_prices,
                             price_stats=price_stats,
                             chart_json=chart_json)
    
    @app.route('/scrape/<int:product_id>', methods=['POST'])
    def scrape_product(product_id):
        """Manually trigger scraping for a specific product."""
        product = db_manager.get_product(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        try:
            # Run scraping in a new event loop (since we're in Flask)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(scraper_manager.scrape_product(product))
            
            # Save results to database
            for site_name, result in results.items():
                if result['success']:
                    db_manager.save_price_history(
                        product_id=product_id,
                        site_name=site_name,
                        price=result['price'],
                        availability=result.get('availability', True),
                        timestamp=datetime.now()
                    )
            
            loop.close()
            
            return jsonify({
                'success': True,
                'results': results,
                'message': 'Scraping completed successfully'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/scrape_all', methods=['POST'])
    def scrape_all_products():
        """Trigger scraping for all products."""
        try:
            products = db_manager.get_all_products()
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            results = loop.run_until_complete(scraper_manager.scrape_all_products(products))
            
            # Save results to database
            total_updated = 0
            for product_id, site_results in results.items():
                for site_name, result in site_results.items():
                    if result['success']:
                        db_manager.save_price_history(
                            product_id=product_id,
                            site_name=site_name,
                            price=result['price'],
                            availability=result.get('availability', True),
                            timestamp=datetime.now()
                        )
                        total_updated += 1
            
            loop.close()
            
            return jsonify({
                'success': True,
                'total_updated': total_updated,
                'message': f'Updated prices for {total_updated} product-site combinations'
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/products')
    def api_products():
        """API endpoint to get all products."""
        products = db_manager.get_all_products()
        return jsonify(products)
    
    @app.route('/api/product/<int:product_id>/prices')
    def api_product_prices(product_id):
        """API endpoint to get price history for a product."""
        days = request.args.get('days', 30, type=int)
        price_history = db_manager.get_price_history(product_id, days)
        return jsonify(price_history)
    
    @app.route('/settings')
    def settings():
        """Settings page."""
        return render_template('settings.html', config=config)
    
    @app.route('/test_notifications', methods=['POST'])
    def test_notifications():
        """Test notification system."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(notification_manager.send_test_notification())
            loop.close()
            
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve the favicon."""
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')
    
    def create_price_chart(price_history, product_name):
        """Create a price history chart using Plotly."""
        if not price_history:
            return json.dumps({})
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(price_history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Create traces for each site
        traces = []
        sites = df['site_name'].unique()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, site in enumerate(sites):
            site_data = df[df['site_name'] == site].sort_values('timestamp')
            
            trace = go.Scatter(
                x=site_data['timestamp'],
                y=site_data['price'],
                mode='lines+markers',
                name=site.title(),
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=6)
            )
            traces.append(trace)
        
        layout = go.Layout(
            title=f'Price History - {product_name}',
            xaxis=dict(title='Date'),
            yaxis=dict(title='Price (USD)'),
            hovermode='closest',
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        fig = go.Figure(data=traces, layout=layout)
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return app
