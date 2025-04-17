from w_modules.wc_sub_routes import subscription_payment_date_mover, bigquery_subscription_processor
from ac_modules.ac_gen_routes import ac_product_field_updater, ac_product_tag_adder
from ac_modules.ac_sub_routes import ac_abo_tag_adder, ac_abo_field_updater
from f_modules.facebook_routes import facebook_audience_customer_adder
from w_modules.wc_gen_routes import bigquery_order_processor
from g_modules.config import determine_script_id
from g_modules.log import end_log, setup_logging
from flask import Flask, request, jsonify
from g_modules.env_tool import env_check
from woocommerce import API
import logging
import time
import os

# Check uitvoering: lokaal of productie
env_check()

# Woocommerce variabelen
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
secret_key = os.getenv('SECRET_KEY')

# Active Campaign variabelen
active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')

# Google variabelen
credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS') 
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

# Facebook variabelen
long_term_token = os.getenv('FACEBOOK_LONG_TERM_ACCESS_TOKEN')
custom_audience_id = os.getenv('FACEBOOK_CUSTOM_AUDIENCE_ID')
ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
app_secret = os.getenv('FACEBOOK_APP_SECRET')
app_id = os.getenv('FACEBOOK_APP_ID')

# Database variabelen
driver = '{ODBC Driver 18 for SQL Server}'
username = os.getenv('GEBRUIKERSNAAM')
database = os.getenv('DATABASE')
password = os.getenv('PASSWORD')
server = os.getenv('SERVER')
greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

# Algemene configuratie
klant = "Aard'g"

# App configuratie
app = Flask(__name__)

# WooCommerce API configuratie
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3",
    timeout=60
)

# Woocommerce Routes
@app.route('/woocommerce/move_next_payment_date', methods=['POST'])
def move_next_payment_date_route():
    return subscription_payment_date_mover(greit_connection_string, klant, secret_key, wcapi)

@app.route('/woocommerce/update_or_add_order_to_bigquery', methods=['POST'])
def order_addition_route():
    return bigquery_order_processor(greit_connection_string, klant, secret_key)

@app.route('/woocommerce/update_or_add_subscription_to_bigquery', methods=['POST'])
def subscription_addition_route():
    return bigquery_subscription_processor(greit_connection_string, klant, secret_key)

# Active Campaign Routes
@app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
def update_ac_abo_field_route():
    return ac_abo_field_updater(greit_connection_string, klant, secret_key, active_campaign_api_url, active_campaign_api_token)

@app.route('/woocommerce/add_abo_tag', methods=['POST'])
def add_abo_tag_route():
    return ac_abo_tag_adder(greit_connection_string, klant, secret_key, active_campaign_api_url, active_campaign_api_token)

@app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
def update_ac_product_fields_route():
    return ac_product_field_updater(greit_connection_string, klant, active_campaign_api_url, active_campaign_api_token, secret_key)

@app.route('/woocommerce/add_ac_product_tag', methods=['POST'])
def add_ac_product_tag_route():
    return ac_product_tag_adder(greit_connection_string, klant, active_campaign_api_url, active_campaign_api_token, secret_key)

# Facebook Routes
@app.route('/woocommerce/add_new_customers_to_facebook_audience', methods=['POST'])
def new_customers_to_facebook_audience_route():
    return facebook_audience_customer_adder(greit_connection_string, klant, secret_key, long_term_token, custom_audience_id, app_secret, app_id)

@app.route('/active_campaign/test', methods=['POST'])
def test_route():
    data = request.form
    # Configuratie
    script = "Product Velden"
    bron = "Active Campaign"
    
    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)
    
    # Set up logging (met database logging)
    db_handler = setup_logging(greit_connection_string, klant, bron, script, script_id)
    logging.info(request.json)
    logging.info(data)
    
    # Logging afhandelen
    db_handler.flush_logs()
    
    return jsonify(request.json)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)
