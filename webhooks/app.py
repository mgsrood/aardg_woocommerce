from flask import Flask, request, jsonify
from woocommerce import API
from dotenv import load_dotenv
import os
from modules.woocommerce_routes import move_next_payment_date
from modules.ac_routes import update_ac_abo_field, update_ac_abo_tag, update_active_campaign_product_fields, add_product_tag_ac
from modules.request_utils import parse_request_data, validate_signature
from modules.facebook_routes import add_new_customers_to_facebook_audience
import logging
from google.cloud import bigquery
import json
import pytz
from datetime import datetime

load_dotenv()

# Load environment variables
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
secret_key = os.getenv('SECRET_KEY')
active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
database_uri = os.getenv('DATABASE_URI')
credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
dataset_id = os.getenv('DATASET_ID')
table_id = os.getenv('TABLE_ID')
app_id = os.getenv('FACEBOOK_APP_ID')
app_secret = os.getenv('FACEBOOK_APP_SECRET')
long_term_token = os.getenv('FACEBOOK_LONG_TERM_ACCESS_TOKEN')
ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
custom_audience_id = os.getenv('FACEBOOK_CUSTOM_AUDIENCE_ID')

# Configuring the app
app = Flask(__name__)

# Configuring the WooCommerce API
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3",
    timeout=60
)

# Initializing BigQuery Client
client = bigquery.Client()
client._http.timeout = 30
table_ref = client.dataset(dataset_id).table(table_id)
table = client.get_table(table_ref)

# Custom logging handler
class BigQueryLoggingHandler(logging.Handler):
    def emit(self, record):
        if record.name in ["urllib3.connectionpool", "apscheduler.scheduler", "werkzeug", "requests"]:
            # Skip these specific logs or handle them differently
            return

        # Converteer de timestamp naar Europe/Amsterdam
        utc_dt = datetime.fromtimestamp(record.created, tz=pytz.utc)
        amsterdam_tz = pytz.timezone('Europe/Amsterdam')
        amsterdam_dt = utc_dt.astimezone(amsterdam_tz)  
        formatted_timestamp = amsterdam_dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] 

        log_entry = {
            "timestamp": formatted_timestamp,
            "log_level": record.levelname,
            "message": record.msg
        }

        try:
            errors = client.insert_rows_json(table, [log_entry])
            if errors:
                self.handleError(record)
        except (json.JSONDecodeError, TypeError) as e:
            # Log JSON formatting errors
            print(f"JSON formatting error: {e} for record: {log_entry}")
        except Exception as e:
            # General error handling for logging
            print(f"Failed to log to BigQuery: {e}")

    def handleError(self, record):
        # Log the problem with logging to BigQuery
        print(f"Failed to log to BigQuery: {record}")


# Set up logging
formatter = logging.Formatter(
    '{"timestamp": "%(asctime)s", "log_level": "%(levelname)s", "message": "%(message)s"}'
)
bigquery_handler = BigQueryLoggingHandler()
bigquery_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(bigquery_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

@app.route('/woocommerce/move_next_payment_date', methods=['POST'])
def payment_date_mover():
    logger.info("Processing move_next_payment_date")
    data = parse_request_data()
    if not data:
        logger.warning("No payload found")
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        logger.warning("Invalid signature")
        return "Invalid signature", 401

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            move_next_payment_date(subscription_data, wcapi)
    
    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
def ac_abo_field_update():
    data = parse_request_data()
    if not data:
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        return "Invalid signature", 401

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            update_ac_abo_field(subscription_data, active_campaign_api_url, active_campaign_api_token)
            logger.info(f"Processed subscription {subscription_id}")
    
    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_abo_tag', methods=['POST'])
def ac_abo_tag_update():
    logger.info("Processing add_abo_tag")
    data = parse_request_data()
    if not data:
        logger.warning("No payload found")
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        logger.warning("Invalid signature")
        return "Invalid signature", 401

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            update_ac_abo_tag(subscription_data, active_campaign_api_url, active_campaign_api_token)
            logger.info(f"Processed subscription {subscription_id}")
    
    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
def ac_product_field_update():
    data = parse_request_data()
    logger.info("Processing update_ac_product_fields")
    if not data:
        logger.warning("No payload found")
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        logger.warning("Invalid signature")
        return "Invalid signature", 401

    if 'id' in data:
        order_id = data['id']
        response = wcapi.get(f"orders/{order_id}")
        if response.status_code == 200:
            order_data = response.json()
            update_active_campaign_product_fields(order_data, active_campaign_api_url, active_campaign_api_token)
            logger.info(f"Processed order {order_id}")
    
    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_ac_product_tag', methods=['POST'])
def ac_product_tag_update():
    logger.info("Processing add_ac_product_tag")
    data = parse_request_data()
    if not data:
        logger.warning("No payload found")
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        logger.warning("Invalid signature")
        return "Invalid signature", 401

    if 'id' in data:
        order_id = data['id']
        response = wcapi.get(f"orders/{order_id}")
        if response.status_code == 200:
            order_data = response.json()
            add_product_tag_ac(order_data, active_campaign_api_url, active_campaign_api_token)
            logger.info(f"Processed order {order_id}")

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_new_customers_to_facebook_audience', methods=['POST'])
def new_customers_to_facebook_audience():
    logger.info("Processing add_new_customers_to_facebook_audience")
    data = parse_request_data()
    if not data:
        logger.warning("No payload found")
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        logger.warning("Invalid signature")
        return "Invalid signature", 401

    if 'id' in data:
        customer_id = data['id']
        response = wcapi.get(f"customers/{customer_id}")
        if response.status_code == 200:
            customer_data = response.json()
            add_new_customers_to_facebook_audience(customer_data, app_id, app_secret, long_term_token, custom_audience_id)
            logger.info(f"Processed customer {customer_data['billing']['first_name'] + ' ' + customer_data['billing']['last_name']}")

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)
