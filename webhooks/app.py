from w_modules.wc_sub_routes import subscription_payment_date_mover, bigquery_subscription_processor
from ac_modules.ac_gen_routes import ac_product_field_updater, ac_product_tag_adder
from ac_modules.ac_sub_routes import ac_abo_tag_adder, ac_abo_field_updater
from f_modules.facebook_routes import facebook_audience_customer_adder
from w_modules.wc_gen_routes import bigquery_order_processor
from g_modules.env_tool import env_check
from g_modules.monitoring import Monitoring
from g_modules.db_metrics import save_metrics_to_db
from flask import Flask, jsonify, Response
from woocommerce import API
import os
from redis import Redis
import json
import time

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
monitoring = Monitoring()

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
@monitoring.track_endpoint_timing
def move_next_payment_date_route():
    return subscription_payment_date_mover(greit_connection_string, klant, secret_key, wcapi)

@app.route('/woocommerce/update_or_add_order_to_bigquery', methods=['POST'])
@monitoring.track_endpoint_timing
def order_addition_route():
    return bigquery_order_processor(greit_connection_string, klant, secret_key)

@app.route('/woocommerce/update_or_add_subscription_to_bigquery', methods=['POST'])
@monitoring.track_endpoint_timing
def subscription_addition_route():
    return bigquery_subscription_processor(greit_connection_string, klant, secret_key)

# Active Campaign Routes
@app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
@monitoring.track_endpoint_timing
def update_ac_abo_field_route():
    return ac_abo_field_updater(greit_connection_string, klant, secret_key, active_campaign_api_url, active_campaign_api_token)

@app.route('/woocommerce/add_abo_tag', methods=['POST'])
@monitoring.track_endpoint_timing
def add_abo_tag_route():
    return ac_abo_tag_adder(greit_connection_string, klant, secret_key, active_campaign_api_url, active_campaign_api_token)

@app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
@monitoring.track_endpoint_timing
def update_ac_product_fields_route():
    return ac_product_field_updater(greit_connection_string, klant, active_campaign_api_url, active_campaign_api_token, secret_key)

@app.route('/woocommerce/add_ac_product_tag', methods=['POST'])
@monitoring.track_endpoint_timing
def add_ac_product_tag_route():
    return ac_product_tag_adder(greit_connection_string, klant, active_campaign_api_url, active_campaign_api_token, secret_key)

# Facebook Routes
@app.route('/woocommerce/add_new_customers_to_facebook_audience', methods=['POST'])
@monitoring.track_endpoint_timing
def new_customers_to_facebook_audience_route():
    return facebook_audience_customer_adder(greit_connection_string, klant, secret_key, long_term_token, custom_audience_id, app_secret, app_id)

# Health check endpoint
@app.route('/health', methods=['GET'])
@monitoring.track_endpoint_timing
def health_check():
    start_time = time.time()
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "app": {"status": "healthy"},
            "redis": {"status": "unknown"},
            "woocommerce": {"status": "unknown"}
        },
        "metrics": {
            "cache": {},
            "endpoints": {},
            "redis_memory": {},
            "errors": {},
            "system": {}
        }
    }

    # Redis check
    try:
        redis_client = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        redis_ping = redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy" if redis_ping else "unhealthy",
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        }
        
        # Voeg cache statistieken toe
        health_status["metrics"]["cache"] = monitoring.get_cache_stats()
        
        # Voeg Redis memory statistieken toe
        health_status["metrics"]["redis_memory"] = monitoring.get_redis_memory_stats()
        
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # WooCommerce check
    try:
        wc_response = wcapi.get("system_status")
        if wc_response.status_code == 200:
            health_status["components"]["woocommerce"] = {
                "status": "healthy",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        else:
            raise Exception(f"Status code: {wc_response.status_code}")
    except Exception as e:
        health_status["components"]["woocommerce"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Voeg endpoint statistieken toe
    health_status["metrics"]["endpoints"] = monitoring.get_endpoint_stats()
    
    # Voeg error statistieken toe
    health_status["metrics"]["errors"] = monitoring.get_error_stats()
    
    # Voeg systeem statistieken toe
    health_status["metrics"]["system"] = monitoring.get_system_stats()

    # Overall latency
    health_status["latency_ms"] = round((time.time() - start_time) * 1000, 2)
    
    # Sla metrics op in database
    try:
        save_metrics_to_db(greit_connection_string, health_status)
    except Exception as e:
        print(f"Error saving metrics: {str(e)}")
        # We laten de health check niet falen als het opslaan mislukt
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return Response(
        json.dumps(health_status, indent=2),
        status=status_code,
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443)
