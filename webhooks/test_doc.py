from woocommerce import API
from dotenv import load_dotenv
import os
import json
import requests
from modules.woocommerce_utils import get_woocommerce_order_data, retrieve_all_products
from modules.ac_utils import get_active_campaign_data, update_active_campaign_fields, product_to_field_map, get_active_campaign_fields, category_to_field_map
from modules.utils import update_field_values, add_or_update_last_ordered_item
from modules.product_utils import get_discount_dict, get_sku_dict, get_key_from_product_id, get_base_unit_values

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

# Get the appropriate dictionaries
sku_dict = get_sku_dict(wcapi)
discount_dict = get_discount_dict(wcapi)
base_unit_values_dict = get_base_unit_values(wcapi)

# Process lineitems to get product and category fields, plus last ordered items
product_line_fields = [
    {"field": product_to_field_map[get_key_from_product_id(item['product_id'], sku_dict)], "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
    for item in line_items if get_key_from_product_id(item['product_id'], sku_dict) in product_to_field_map
]

discount_line_fields = [
    {"field": '11', "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
    for item in line_items if get_key_from_product_id(item['product_id'], discount_dict) in category_to_field_map
]

orderbump_line_fields = [
    {"field": '12', "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
    for item in line_items 
    if any(meta['key'] == '_bump_purchase' for meta in item.get('meta_data', []))
]

fkcart_upsell_line_fields = [
    {"field": '22', "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
    for item in line_items 
    if any(meta['key'] == '_fkcart_upsell' for meta in item.get('meta_data', []))
]

last_ordered_item = ["P_" + get_key_from_product_id(item['product_id'], sku_dict) for item in line_items]
last_ordered_item = ','.join(last_ordered_item)

# Retrieve ActiveCampaign data
active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
active_campaign_id = active_campaign_data['contacts'][0]['id']
field_values = get_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token)['fieldValues']
current_fields = [
    {"field": item['field'], "value": item['value'], "id": item['id']}
    for item in field_values
]
current_fields = sorted(current_fields, key=lambda x: int(x['field']))

# Update fields
updated_fields, new_fields = update_field_values(current_fields, product_line_fields + discount_line_fields + orderbump_line_fields + fkcart_upsell_line_fields)
updated_fields, new_fields = add_or_update_last_ordered_item(updated_fields, new_fields, last_ordered_item)

# Push updates to ActiveCampaign
update_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token, updated_fields, new_fields)


