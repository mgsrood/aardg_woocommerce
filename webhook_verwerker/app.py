from active_campaign.functions import (
    update_active_campaign_product_fields, 
    add_product_tag_ac, 
    update_ac_abo_field, 
    update_ac_abo_tag,
    add_originals_dummy_product
)
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

"""@app.route('/woocommerce/update_ac_product_fields', methods=['POST'])
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

@app.route('/woocommerce/update_ac_abo_field', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='Abonnements Veld', 
    process_func=update_ac_abo_field)
def process_ac_abonnement_velden():
    pass

@app.route('/woocommerce/add_abo_tag', methods=['POST'])
@initialize_route(
    woo_config, 
    bron='Active Campaign', 
    script='AC Abonnement Tags Update', 
    process_func=update_ac_abo_tag)
def process_ac_abonnement_tags():
    pass"""

@app.route('/active_campaign/add_dummy_product', methods=['POST'])
@initialize_route(
    campaign_config, 
    bron='Active Campaign', 
    script='Originals', 
    process_func=add_originals_dummy_product)
def process_originals_dummy_product():
    pass

if __name__ == '__main__':
    app.run(debug=True, port=5010)