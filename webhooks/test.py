from woocommerce import API
from dotenv import load_dotenv
import os
import json
import requests
from modules.woocommerce_utils import get_woocommerce_order_data
from modules.catalog_generator import retrieve_all_products, save_catalogue_to_json


load_dotenv()

# Load environment variables
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')

# Configuring the WooCommerce API
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3",
    timeout=60
)

# Get WooCommerce Data
order_id = '99384'
woocommerce_data = get_woocommerce_order_data(order_id, wcapi)
line_items = woocommerce_data['line_items']
email = 'mgsrood@gmail.com'

# Test productcatalogue
product_catalogue, products = retrieve_all_products(wcapi)
print(json.dumps(product_catalogue, indent=4))
print(json.dumps(products, indent=4))