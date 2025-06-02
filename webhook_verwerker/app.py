from active_campaign.functions import (
    update_active_campaign_product_fields, 
    add_product_tag_ac, 
    increase_ac_abo_field, 
    decrease_ac_abo_field,
    add_ac_abo_tag,
    add_originals_dummy_product
)
from woocommerce_.functions import (
    move_next_payment_date,
    update_or_insert_sub_to_bigquery,
    update_or_insert_order_to_bigquery
)
from facebook.functions import add_new_customers_to_facebook_audience
from scripts.catalog_generator import main as generate_catalog_main 
from apscheduler.schedulers.background import BackgroundScheduler
from utils.route_initializer import RouteConfig, initialize_route
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Environment variables
secret_key = os.getenv('SECRET_KEY')

# Route configuraties
woo_config = RouteConfig(
    verify_signature=True,
    parse_data=True,
    secret_key=secret_key
)

campaign_config = RouteConfig(
    verify_signature=False,
    parse_data=True,
    secret_key=None
)

facebook_config = RouteConfig(
    verify_signature=False,
    parse_data=True,
    secret_key=secret_key
)

@app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='AC Product Fields Update', 
    process_func=update_active_campaign_product_fields)
def process_ac_product_fields():
    pass

@app.route('/woocommerce/add_ac_product_tag', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='AC Product Tags Update', 
    process_func=add_product_tag_ac)
def process_ac_product_tags():
    pass

@app.route('/woocommerce/increase_ac_abo_field', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='Abonnements Veld Ophogen', 
    process_func=increase_ac_abo_field)
def process_ac_abonnement_velden_ophogen():
    pass

@app.route('/woocommerce/decrease_ac_abo_field', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='Abonnements Veld Verlagen', 
    process_func=decrease_ac_abo_field)
def process_ac_abonnement_velden_verlagen():
    pass

@app.route('/woocommerce/add_abo_tag', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='AC Abonnement Tags Update', 
    process_func=add_ac_abo_tag)
def process_ac_abonnement_tags_add():
    pass

@app.route('/active_campaign/add_product', methods=['POST'])
@initialize_route(
    campaign_config, 
    bron='Active Campaign', 
    script='Originals', 
    process_func=add_originals_dummy_product)
def process_originals_dummy_product():
    pass

@app.route('/woocommerce/move_next_payment_date', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='WooCommerce', 
    script='Betaaldatum Verplaatsen', 
    process_func=move_next_payment_date)
def process_move_next_payment_date():
    pass

@app.route('/woocommerce/sync_subscription_to_bigquery', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='BigQuery', 
    script='Synchroniseer Abonnement', 
    process_func=update_or_insert_sub_to_bigquery)
def process_sync_subscription_to_bigquery():
    pass

@app.route('/woocommerce/sync_order_to_bigquery', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='BigQuery', 
    script='Synchroniseer Order', 
    process_func=update_or_insert_order_to_bigquery)
def process_sync_order_to_bigquery():
    pass

@app.route('/woocommerce/add_new_customers_to_facebook_audience', methods=['POST'])
@initialize_route(
    facebook_config,
    bron='Facebook',
    script='Facebook Audience Update',
    process_func=add_new_customers_to_facebook_audience)
def process_facebook_audience_update():
    pass

def run_catalog_generation_job():
    try:
        generate_catalog_main()
    except Exception as e:
        print(f"APScheduler: Error during product catalog generation job: {e}") 

if __name__ == '__main__':
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(run_catalog_generation_job, 'interval', minutes=1440, id="catalog_generator_job")
    scheduler.start()
    print("APScheduler started. Catalog generation job scheduled every day at 03:00.")
    
    use_reloader = app.debug 
    app.run(debug=app.debug, port=5010, use_reloader=not use_reloader)