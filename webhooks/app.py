from w_modules.wc_sub_routes import subscription_payment_date_mover, bigquery_subscription_processor
from ac_modules.ac_gen_routes import ac_product_field_updater, ac_product_tag_adder
from ac_modules.ac_sub_routes import ac_abo_tag_adder, ac_abo_field_updater
from f_modules.facebook_routes import facebook_audience_customer_adder
from w_modules.wc_gen_routes import bigquery_order_processor
from g_modules.env_tool import env_check
from flask import Flask, jsonify, request
from typing import Dict, Any, Tuple
from woocommerce import API
import logging
import os

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Application configuration management"""
    def __init__(self):
        # Check environment: local or production
        env_check()
        
        # WooCommerce configuration
        self.woocommerce = {
            'url': os.getenv('WOOCOMMERCE_URL'),
            'consumer_key': os.getenv('WOOCOMMERCE_CONSUMER_KEY'),
            'consumer_secret': os.getenv('WOOCOMMERCE_CONSUMER_SECRET'),
            'secret_key': os.getenv('SECRET_KEY')
        }
        
        # Active Campaign configuration
        self.active_campaign = {
            'api_token': os.getenv('ACTIVE_CAMPAIGN_API_TOKEN'),
            'api_url': os.getenv('ACTIVE_CAMPAIGN_API_URL')
        }
        
        # Google configuration
        credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # Facebook configuration
        self.facebook = {
            'long_term_token': os.getenv('FACEBOOK_LONG_TERM_ACCESS_TOKEN'),
            'custom_audience_id': os.getenv('FACEBOOK_CUSTOM_AUDIENCE_ID'),
            'ad_account_id': os.getenv('FACEBOOK_AD_ACCOUNT_ID'),
            'app_secret': os.getenv('FACEBOOK_APP_SECRET'),
            'app_id': os.getenv('FACEBOOK_APP_ID')
        }
        
        # Database configuration
        self.database = {
            'driver': '{ODBC Driver 18 for SQL Server}',
            'username': os.getenv('GEBRUIKERSNAAM'),
            'database': os.getenv('DATABASE'),
            'password': os.getenv('PASSWORD'),
            'server': os.getenv('SERVER')
        }
        
        # Validate configuration
        self._validate_config()
        
        # Build connection string
        self.connection_string = self._build_connection_string()
        
        # General configuration
        self.klant = "Aard'g"
        self.script_id = 1

    def _validate_config(self) -> None:
        """Validate that all required environment variables are set"""
        required_vars = {
            'WooCommerce': ['WOOCOMMERCE_URL', 'WOOCOMMERCE_CONSUMER_KEY', 'WOOCOMMERCE_CONSUMER_SECRET', 'SECRET_KEY'],
            'Active Campaign': ['ACTIVE_CAMPAIGN_API_TOKEN', 'ACTIVE_CAMPAIGN_API_URL'],
            'Google': ['AARDG_GOOGLE_CREDENTIALS'],
            'Facebook': ['FACEBOOK_LONG_TERM_ACCESS_TOKEN', 'FACEBOOK_CUSTOM_AUDIENCE_ID', 'FACEBOOK_APP_SECRET', 'FACEBOOK_APP_ID'],
            'Database': ['GEBRUIKERSNAAM', 'DATABASE', 'PASSWORD', 'SERVER']
        }
        
        for section, vars in required_vars.items():
            for var in vars:
                if not os.getenv(var):
                    raise ValueError(f"Missing required environment variable: {var} in {section} configuration")

    def _build_connection_string(self) -> str:
        """Build database connection string"""
        return (f"DRIVER={self.database['driver']};"
                f"SERVER={self.database['server']};"
                f"DATABASE={self.database['database']};"
                f"UID={self.database['username']};"
                f"PWD={self.database['password']};"
                "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;")

def create_app() -> Flask:
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Initialize configuration
    config = Config()
    
    # Initialize WooCommerce API
    wcapi = API(
        url=config.woocommerce['url'],
        consumer_key=config.woocommerce['consumer_key'],
        consumer_secret=config.woocommerce['consumer_secret'],
        version="wc/v3",
        timeout=60
    )

    def handle_api_error(func):
        """Decorator for consistent API error handling"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                return jsonify({"error": str(e)}), 500
        wrapper.__name__ = func.__name__
        return wrapper

    # WooCommerce Routes
    @app.route('/woocommerce/move_next_payment_date', methods=['POST'])
    @handle_api_error
    def move_next_payment_date_route():
        return subscription_payment_date_mover(config.connection_string, config.klant, wcapi, config.woocommerce['secret_key'])

    @app.route('/woocommerce/update_or_add_order_to_bigquery', methods=['POST'])
    @handle_api_error
    def order_addition_route():
        return bigquery_order_processor(config.connection_string, config.klant, wcapi, config.woocommerce['secret_key'])

    @app.route('/woocommerce/update_or_add_subscription_to_bigquery', methods=['POST'])
    @handle_api_error
    def subscription_addition_route():
        return bigquery_subscription_processor(config.connection_string, config.klant, wcapi, config.woocommerce['secret_key'])

    # Active Campaign Routes
    @app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
    @handle_api_error
    def update_ac_abo_field_route():
        return ac_abo_field_updater(
            config.connection_string, config.klant, wcapi, 
            config.woocommerce['secret_key'], 
            config.active_campaign['api_url'], 
            config.active_campaign['api_token']
        )

    @app.route('/woocommerce/add_abo_tag', methods=['POST'])
    @handle_api_error
    def add_abo_tag_route():
        return ac_abo_tag_adder(
            config.connection_string, config.klant, wcapi, 
            config.woocommerce['secret_key'], 
            config.active_campaign['api_url'], 
            config.active_campaign['api_token']
        )

    @app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
    @handle_api_error
    def update_ac_product_fields_route():
        return ac_product_field_updater(
            config.connection_string, config.klant, wcapi,
            config.active_campaign['api_url'],
            config.active_campaign['api_token'],
            config.woocommerce['secret_key']
        )

    @app.route('/woocommerce/add_ac_product_tag', methods=['POST'])
    @handle_api_error
    def add_ac_product_tag_route():
        return ac_product_tag_adder(
            config.connection_string, config.klant, wcapi,
            config.active_campaign['api_url'],
            config.active_campaign['api_token'],
            config.woocommerce['secret_key']
        )

    # Facebook Routes
    @app.route('/woocommerce/add_new_customers_to_facebook_audience', methods=['POST'])
    @handle_api_error
    def new_customers_to_facebook_audience_route():
        return facebook_audience_customer_adder(
            config.connection_string, config.klant, wcapi,
            config.woocommerce['secret_key'],
            config.facebook['long_term_token'],
            config.facebook['custom_audience_id'],
            config.facebook['app_secret'],
            config.facebook['app_id']
        )

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8443)
