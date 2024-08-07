from flask import Flask, request, jsonify
from woocommerce import API
import requests
from dotenv import load_dotenv
import os
import json
import hmac
import hashlib
import base64
from subscription_utils import move_next_payment_date, update_ac_abo_field
import flask_monitoringdashboard as dashboard
import logging

logging.basicConfig(level=logging.DEBUG)

load_dotenv()

# Load environment variables
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
secret_key = os.getenv('SECRET_KEY')
ac_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
ac_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
database_uri = os.getenv('DATABASE_URI')

# Configuring the app
app = Flask(__name__)

# Configuring the WooCommerce API
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3"
)

def validate_signature(request, secret):
    payload = request.get_data()
    signature = request.headers.get('X-WC-Webhook-Signature')
    computed_signature = base64.b64encode(hmac.new(secret.encode(), payload, hashlib.sha256).digest()).decode()
    return hmac.compare_digest(signature, computed_signature)

@app.route('/')
def hello_world():
    logging.info("hello_world endpoint was called.")	
    return "hello world"

@app.route('/woocommerce/move_next_payment_date', methods=['POST'])
def payment_date_mover():
    content_type = request.headers.get('Content-Type')

    data = None
    if content_type == 'application/json':
        data = request.get_json(silent=True)
    elif content_type == 'application/x-www-form-urlencoded':
        form_data = request.form.to_dict(flat=False)
        for key in form_data:
            try:
                data = json.loads(key)
                break
            except json.JSONDecodeError:
                continue
    else:
        return "Unsupported Media Type", 415

    if not data:
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        return "Invalid signature", 401

    if 'id' in data:  # Check if it is a valid subscription
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            move_next_payment_date(subscription_data, wcapi)

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
def ac_abo_field_update():
    content_type = request.headers.get('Content-Type')

    data = None
    if content_type == 'application/json':
        data = request.get_json(silent=True)
    elif content_type == 'application/x-www-form-urlencoded':
        form_data = request.form.to_dict(flat=False)
        for key in form_data:
            try:
                data = json.loads(key)
                break
            except json.JSONDecodeError:
                continue
    else:
        return "Unsupported Media Type", 415

    if not data:
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        return "Invalid signature", 401

    if 'id' in data:  # Check if it is a valid subscription
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            update_ac_abo_field(subscription_data, ac_api_url, ac_api_token)

    return jsonify({'status': 'success'}), 200

# Configure Flask Monitoring Dashboard
dashboard.config.init_from(file='/home/maxrood/codering/aardg/projecten/woocommerce/webhooks/config.cfg')
dashboard.bind(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)
