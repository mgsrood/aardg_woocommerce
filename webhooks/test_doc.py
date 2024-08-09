from woocommerce import API
from dotenv import load_dotenv
import os
import json
import requests
from modules.woocommerce_utils import get_woocommerce_subscription_data
from modules.ac_utils import get_active_campaign_data, add_tag_to_contact, get_active_campaign_tag_data
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
    version="wc/v3"
)

# Get WooCommerce Data
subscription_id = '4889'
woocommerce_data = get_woocommerce_subscription_data(subscription_id, wcapi)
line_items = woocommerce_data['line_items']
email = woocommerce_data.get('billing', {}).get('email')

# Get ActiveCampaign ID
active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
active_campaign_id = active_campaign_data['contacts'][0]['id']

# Add Abo tag
abo_tag_id = 115
tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]

add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)
