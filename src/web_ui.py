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
import hmac
import hashlib
from functools import wraps
from flask import request, jsonify

from .database import DatabaseManager
from .config import Config
from .scraper_manager import ScraperManager
from .notification import NotificationManager
from .shopping_list import AutoShoppingListGenerator
from .utils import format_price, group_results_by_status


def create_app():
    """Create Flask application."""
    # Get the project root directory (parent of src)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    
    app = Flask(__name__, template_folder=template_dir)
    app.config['SECRET_KEY'] = 'your-secret-key-change-this'
    
    # Initialize configuration with error handling
    config = Config()
    
    # Check for configuration errors
    if config.has_config_error():
        @app.route('/')
        def setup_required():
            """Show setup page when configuration is missing or invalid."""
            return render_template('setup.html', 
                                 error=config.get_config_error(),
                                 config_path=config.config_path)
        
        @app.route('/create-config', methods=['POST'])
        def create_config():
            """Create a default configuration file."""
            success = config.create_default_config_file()
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'Default configuration file created successfully. Please restart the application.'
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Failed to create configuration file. Check file permissions.'
                })
        
        @app.route('/health')
        def health_check():
            """Health check endpoint."""
            return jsonify({'status': 'error', 'message': 'Configuration required'})
        
        return app
    
    # Initialize other components only if config is valid
    db_manager = DatabaseManager(config.database_path)
    scraper_manager = ScraperManager(config)
    notification_manager = NotificationManager(config)
    shopping_list_generator = AutoShoppingListGenerator(db_manager, notification_manager)
    
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
    
    @app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
    def edit_product(product_id):
        """Edit an existing product."""
        product = db_manager.get_product(product_id)
        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))
        
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
                return render_template('edit_product.html', form=form, product=product)
            
            try:
                db_manager.update_product(
                    product_id=product_id,
                    name=form.name.data,
                    description=form.description.data,
                    target_price=form.target_price.data,
                    urls=urls
                )
                flash(f'Product "{form.name.data}" updated successfully!', 'success')
                return redirect(url_for('product_detail', product_id=product_id))
            except Exception as e:
                flash(f'Error updating product: {str(e)}', 'error')
        
        # Pre-populate form with existing data
        if request.method == 'GET':
            form.name.data = product['name']
            form.description.data = product['description']
            form.target_price.data = product['target_price']
            
            # URLs are already parsed as a dictionary by the database method
            urls = product['urls'] if product['urls'] else {}
            form.jjfoodservice_url.data = urls.get('jjfoodservice', '')
            form.atoz_catering_url.data = urls.get('atoz_catering', '')
            form.amazon_uk_url.data = urls.get('amazon_uk', '')
        
        return render_template('edit_product.html', form=form, product=product)
    
    @app.route('/delete_product/<int:product_id>', methods=['POST'])
    def delete_product(product_id):
        """Delete a product."""
        product = db_manager.get_product(product_id)
        if not product:
            flash('Product not found.', 'error')
            return redirect(url_for('index'))
        
        try:
            db_manager.delete_product(product_id)
            flash(f'Product "{product["name"]}" deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting product: {str(e)}', 'error')
        
        return redirect(url_for('index'))
    
    @app.route('/shopping-lists')
    def shopping_lists():
        """Display automated shopping lists based on best prices."""
        try:
            shopping_lists = shopping_list_generator.generate_shopping_lists()
            summary = shopping_list_generator.get_summary_stats()
            
            return render_template('shopping_lists.html', 
                                 shopping_lists=shopping_lists,
                                 summary=summary)
        except Exception as e:
            flash(f'Error generating shopping lists: {str(e)}', 'danger')
            return redirect(url_for('index'))
    
    @app.route('/shopping-list/<store_name>')
    def shopping_list_detail(store_name):
        """Display detailed shopping list for a specific store."""
        try:
            shopping_lists = shopping_list_generator.generate_shopping_lists()
            store_list = next((sl for sl in shopping_lists if sl.store_name == store_name), None)
            
            if not store_list:
                flash(f'No items found for {store_name}', 'warning')
                return redirect(url_for('shopping_lists'))
            
            return render_template('shopping_list_detail.html',
                                 shopping_list=store_list,
                                 store_name=store_name)
        except Exception as e:
            flash(f'Error loading shopping list: {str(e)}', 'danger')
            return redirect(url_for('shopping_lists'))
    
    @app.route('/send-daily-shopping-list', methods=['POST'])
    def send_daily_shopping_list():
        """Send daily shopping list via email/webhook."""
        try:
            success = shopping_list_generator.send_daily_shopping_list()
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Daily shopping list sent successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Failed to send daily shopping list. Check notification settings.'
                })
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/shopping-lists')
    def api_shopping_lists():
        """API endpoint for shopping lists data."""
        try:
            shopping_lists = shopping_list_generator.generate_shopping_lists()
            summary = shopping_list_generator.get_summary_stats()
            
            # Convert to JSON-serializable format
            data = {
                'summary': {
                    'total_products': summary['total_products'],
                    'total_cost': summary['total_cost'],
                    'total_savings': summary['total_savings'],
                    'store_count': summary['store_count'],
                    'most_items_store': summary['most_items_store'],
                    'most_items_count': summary['most_items_count'],
                    'generated_at': summary['generated_at'].isoformat()
                },
                'store_lists': []
            }
            
            for store_list in shopping_lists:
                store_data = {
                    'store_name': store_list.store_name,
                    'store_display_name': store_list.store_display_name,
                    'base_url': store_list.base_url,
                    'total_cost': store_list.total_cost,
                    'total_savings': store_list.total_savings,
                    'item_count': store_list.item_count,
                    'items': []
                }
                
                for item in store_list.items:
                    item_data = {
                        'product_id': item.product_id,
                        'product_name': item.product_name,
                        'current_price': item.current_price,
                        'store_url': item.store_url,
                        'last_updated': item.last_updated.isoformat(),
                        'savings_vs_most_expensive': item.savings_vs_most_expensive
                    }
                    store_data['items'].append(item_data)
                
                data['store_lists'].append(store_data)
            
            return jsonify(data)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # Add webhook authentication decorator
    def webhook_auth_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get webhook secret from environment
            webhook_secret = os.environ.get('WEBHOOK_SECRET', 'your-secret-key-here')
            
            # Check for secret in header or query parameter
            provided_secret = request.headers.get('X-Webhook-Secret') or request.args.get('secret')
            
            if not provided_secret or provided_secret != webhook_secret:
                return jsonify({'error': 'Unauthorized'}), 401
            
            return f(*args, **kwargs)
        return decorated_function

    # Add webhook routes
    @app.route('/webhook/scrape', methods=['POST', 'GET'])
    @webhook_auth_required
    def webhook_scrape():
        """Webhook endpoint to trigger price scraping"""
        try:
            # Run scraping in background
            import asyncio
            from .scraper_manager import ScraperManager
            from .notification import NotificationManager
            
            async def run_scrape():
                try:
                    logger.info("Webhook triggered price scraping")
                    
                    config = Config()
                    if config.has_config_error():
                        logger.error(f"Configuration error: {config.get_config_error()}")
                        return {'error': 'Configuration error'}
                    
                    db_manager = DatabaseManager(config.database_path)
                    scraper_manager = ScraperManager(config)
                    notification_manager = NotificationManager(config)
                    
                    products = db_manager.get_all_products()
                    if not products:
                        logger.warning("No products found to scrape")
                        return {'message': 'No products to scrape'}
                    
                    logger.info(f"Scraping {len(products)} products")
                    results = await scraper_manager.scrape_all_products(products)
                    
                    total = sum(len(sites) for sites in results.values())
                    successful = sum(1 for sites in results.values() for result in sites.values() if result['success'])
                    failed = total - successful
                    
                    logger.info(f"Scraping complete: {successful}/{total} successful")
                    
                    # Save results and collect price alerts
                    price_alerts = []
                    for product_id, site_results in results.items():
                        product = db_manager.get_product(product_id)
                        for site_name, result in site_results.items():
                            if result['success']:
                                # Save to database
                                db_manager.save_price_history(
                                    product_id=product_id,
                                    site_name=site_name,
                                    price=result['price'],
                                    availability=result.get('availability', True),
                                    timestamp=datetime.now()
                                )
                                
                                # Check for price alerts
                                if product and product.get('target_price') and result['price'] <= product['target_price']:
                                    price_alerts.append({
                                        'product': product,
                                        'site': site_name,
                                        'current_price': result['price'],
                                        'target_price': product['target_price'],
                                        'url': result.get('url', '')
                                    })
                    
                    # Send price alerts if any
                    if price_alerts:
                        alert_message = "Price Alerts:\n\n"
                        for alert in price_alerts:
                            alert_message += f"🎯 {alert['product']['name']}\n"
                            alert_message += f"   Store: {alert['site']}\n"
                            alert_message += f"   Price: £{alert['current_price']} (Target: £{alert['target_price']})\n"
                            alert_message += f"   URL: {alert['url']}\n\n"
                        
                        await notification_manager.send_notification(
                            subject=f"Price Alert: {len(price_alerts)} item(s) on sale!",
                            message=alert_message
                        )
                        logger.info(f"Sent price alerts for {len(price_alerts)} items")
                    
                    # Send scraping summary
                    summary_message = f"Daily Price Scraping Summary:\n\n"
                    summary_message += f"📊 Products scraped: {len(products)}\n"
                    summary_message += f"✅ Successful: {successful}\n"
                    summary_message += f"❌ Failed: {failed}\n"
                    summary_message += f"🎯 Price alerts: {len(price_alerts)}\n"
                    summary_message += f"🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    
                    await notification_manager.send_notification(
                        subject="Daily Price Scraping Complete",
                        message=summary_message
                    )
                    logger.info("Sent scraping summary")
                    
                    return {
                        'message': 'Scraping completed successfully',
                        'total_products': len(products),
                        'successful': successful,
                        'failed': failed,
                        'price_alerts': len(price_alerts)
                    }
                    
                except Exception as e:
                    logger.error(f"Webhook scraping failed: {str(e)}", exc_info=True)
                    
                    # Send error notification
                    try:
                        await notification_manager.send_notification(
                            subject="Price Scraping Failed",
                            message=f"Daily price scraping failed with error:\n\n{str(e)}"
                        )
                    except:
                        pass
                    
                    return {'error': str(e)}
            
            # Run the async function
            result = asyncio.run(run_scrape())
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/webhook/shopping-list', methods=['POST', 'GET'])
    @webhook_auth_required
    def webhook_shopping_list():
        """Webhook endpoint to send daily shopping list"""
        try:
            from .shopping_list import AutoShoppingListGenerator
            from .notification import NotificationManager
            
            config = Config()
            if config.has_config_error():
                return jsonify({'error': 'Configuration error'}), 500
            
            db_manager = DatabaseManager(config.database_path)
            shopping_list_generator = AutoShoppingListGenerator(db_manager)
            notification_manager = NotificationManager(config)
            
            # Generate shopping lists
            shopping_lists = shopping_list_generator.generate_all_shopping_lists()
            
            if shopping_lists:
                shopping_message = "Daily Shopping List (Best Prices):\n\n"
                total_savings = 0
                
                for store_name, store_list in shopping_lists.items():
                    if store_list.items:
                        shopping_message += f"🏪 {store_name.upper()}:\n"
                        store_total = 0
                        for item in store_list.items:
                            shopping_message += f"   • {item.product_name} - £{item.current_price}\n"
                            store_total += item.current_price
                            if item.savings_amount > 0:
                                total_savings += item.savings_amount
                        shopping_message += f"   Subtotal: £{store_total:.2f}\n\n"
                
                if total_savings > 0:
                    shopping_message += f"💰 Total Savings: £{total_savings:.2f}\n"
                
                # Send email using asyncio
                async def send_email():
                    await notification_manager.send_notification(
                        subject="Daily Shopping List - Best Prices",
                        message=shopping_message
                    )
                
                asyncio.run(send_email())
                
                return jsonify({
                    'message': 'Shopping list sent successfully',
                    'stores': list(shopping_lists.keys()),
                    'total_savings': total_savings
                })
            else:
                return jsonify({'message': 'No shopping lists generated'})
                
        except Exception as e:
            logger.error(f"Shopping list webhook error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/webhook/scrape-and-list', methods=['POST', 'GET'])
    @webhook_auth_required
    def webhook_scrape_and_list():
        """Webhook endpoint to scrape prices AND send shopping list"""
        try:
            # First trigger scraping
            scrape_response = webhook_scrape()
            scrape_data = scrape_response.get_json()
            
            if 'error' in scrape_data:
                return jsonify({'scraping_error': scrape_data['error']}), 500
            
            # Then send shopping list
            list_response = webhook_shopping_list()
            list_data = list_response.get_json()
            
            return jsonify({
                'message': 'Scraping and shopping list completed',
                'scraping': scrape_data,
                'shopping_list': list_data
            })
            
        except Exception as e:
            logger.error(f"Combined webhook error: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/webhook/health', methods=['GET'])
    def webhook_health():
        """Health check endpoint for webhooks"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'endpoints': [
                '/webhook/scrape',
                '/webhook/shopping-list', 
                '/webhook/scrape-and-list'
            ]
        })
    
    return app
