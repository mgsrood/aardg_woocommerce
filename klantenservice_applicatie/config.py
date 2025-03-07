import os
from dotenv import load_dotenv

# Laad environment variables
load_dotenv()

class Config:
    # Basis Flask configuratie
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Database configuratie
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'woocommerce.db')
    
    # Cache configuratie
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minuten
    
    # WooCommerce API configuratie
    WC_CONSUMER_KEY = os.getenv('WC_CONSUMER_KEY')
    WC_CONSUMER_SECRET = os.getenv('WC_CONSUMER_SECRET')
    WC_API_URL = os.getenv('WC_API_URL')
    
    # Gebruik SQLite als standaard
    USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true' 