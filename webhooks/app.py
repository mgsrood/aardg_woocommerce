from flask import Flask, request, jsonify
from woocommerce import API
from dotenv import load_dotenv
import os
from modules.woocommerce_routes import move_next_payment_date, add_abo_to_bigquery, update_abo_in_bigquery
from modules.ac_routes import update_ac_abo_field, update_ac_abo_tag, update_active_campaign_product_fields, add_product_tag_ac
from modules.request_utils import parse_request_data, validate_signature
from modules.facebook_routes import add_new_customers_to_facebook_audience
from modules.database import connect_to_database
from modules.config import fetch_script_id
from modules.log import log
import time
from datetime import timedelta

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
app_id = os.getenv('FACEBOOK_APP_ID')
app_secret = os.getenv('FACEBOOK_APP_SECRET')
long_term_token = os.getenv('FACEBOOK_LONG_TERM_ACCESS_TOKEN')
ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
custom_audience_id = os.getenv('FACEBOOK_CUSTOM_AUDIENCE_ID')
bron = "Backend Applicatie"
klant = "Aard'g"
script_id = 1
server = os.getenv('SERVER')
database = os.getenv('DATABASE')
username = os.getenv('GEBRUIKERSNAAM')
password = os.getenv('PASSWORD')
driver = '{ODBC Driver 18 for SQL Server}'
greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

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

@app.route('/woocommerce/move_next_payment_date', methods=['POST'])
def payment_date_mover():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start move_next_payment_date", "Volgende betaaldatum verplaatsen", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij move_next_payment_date", "Volgende betaaldatum verplaatsen", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij move_next_payment_date", "Volgende betaaldatum verplaatsen", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            move_next_payment_date(subscription_data, wcapi, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Abonnement {subscription_id} verwerkt", "Volgende betaaldatum verplaatsen", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Volgende betaaldatum verplaatsen", script_id)

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_subscription_to_bigquery', methods=['POST'])
def subscription_adder():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start add_subscription_to_bigquery", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij add_subscription_to_bigquery", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij add_subscription_to_bigquery", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            add_abo_to_bigquery(subscription_data, credentials_path, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Abonnement {subscription_id} verwerkt", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Abonnement toevoegen aan BigQuery", script_id)
    
    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
def ac_abo_field_update():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start update_ac_abo_field", "Active Campaign abonnement veld bijwerken", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij update_ac_abo_field", "Active Campaign abonnement veld bijwerken", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij update_ac_abo_field", "Active Campaign abonnement veld bijwerken", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            update_ac_abo_field(data, active_campaign_api_url, active_campaign_api_token, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Abonnement {subscription_id} verwerkt", "Active Campaign abonnement veld bijwerken", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Active Campaign abonnement veld bijwerken", script_id)

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_abo_tag', methods=['POST'])
def ac_abo_tag_update():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start add_abo_tag", "Active Campaign abonnement tag bijwerken", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij add_abo_tag", "Active Campaign abonnement tag bijwerken", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij add_abo_tag", "Active Campaign abonnement tag bijwerken", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            update_ac_abo_tag(subscription_data, active_campaign_api_url, active_campaign_api_token, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Abonnement {subscription_id} verwerkt", "Active Campaign abonnement tag bijwerken", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Active Campaign abonnement tag bijwerken", script_id)

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
def ac_product_field_update():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    data = parse_request_data()
    log(greit_connection_string, klant, bron, "Start update_ac_product_fields", "Active Campaign product velden bijwerken", script_id, tabel=None)
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij update_ac_product_fields", "Active Campaign product velden bijwerken", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij update_ac_product_fields", "Active Campaign product velden bijwerken", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        order_id = data['id']
        response = wcapi.get(f"orders/{order_id}")
        if response.status_code == 200:
            order_data = response.json()
            update_active_campaign_product_fields(order_data, active_campaign_api_url, active_campaign_api_token, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Order {order_id} verwerkt", "Active Campaign product velden bijwerken", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Active Campaign product velden bijwerken", script_id)

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_ac_product_tag', methods=['POST'])
def ac_product_tag_update():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start add_ac_product_tag", "Active Campaign product tag bijwerken", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij add_ac_product_tag", "Active Campaign product tag bijwerken", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij add_ac_product_tag", "Active Campaign product tag bijwerken", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        order_id = data['id']
        response = wcapi.get(f"orders/{order_id}")
        if response.status_code == 200:
            order_data = response.json()
            add_product_tag_ac(order_data, active_campaign_api_url, active_campaign_api_token, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Order {order_id} verwerkt", "Active Campaign product tag bijwerken", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Active Campaign product tag bijwerken", script_id)


    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/add_new_customers_to_facebook_audience', methods=['POST'])
def new_customers_to_facebook_audience():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start add_new_customers_to_facebook_audience", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij add_new_customers_to_facebook_audience", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij add_new_customers_to_facebook_audience", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        customer_id = data['id']
        response = wcapi.get(f"customers/{customer_id}")
        if response.status_code == 200:
            customer_data = response.json()
            add_new_customers_to_facebook_audience(customer_data, app_id, app_secret, long_term_token, custom_audience_id, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Klant {customer_data['billing']['first_name'] + ' ' + customer_data['billing']['last_name']} verwerkt", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Nieuwe klanten toevoegen aan Facebook audience", script_id)

    return jsonify({'status': 'success'}), 200

@app.route('/woocommerce/update_subscription_in_bigquery', methods=['POST'])
def subscription_updater():
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    
    log(greit_connection_string, klant, bron, "Start update_subscription_in_bigquery", "Abonnement updaten in BigQuery", script_id, tabel=None)
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden bij add_subscription_to_bigquery", "Abonnement updaten in BigQuery", script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening bij add_subscription_to_bigquery", "Abonnement updaten in BigQuery", script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)

    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        if response.status_code == 200:
            subscription_data = response.json()
            update_abo_in_bigquery(subscription_data, credentials_path, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Abonnement {subscription_id} verwerkt", "Abonnement updaten in BigQuery", script_id, tabel=None)
            eindtijd = time.time()
            tijdsduur = timedelta(seconds=(eindtijd - start_time))
            tijdsduur_str = str(tijdsduur).split('.')[0]
            log(greit_connection_string, klant, bron, f"Script gestopt in {tijdsduur_str}", "Abonnement updaten in BigQuery", script_id)
    
    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)
