from woocommerce import API
from subscription_utils import move_next_payment_date
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta
import requests

load_dotenv()

# Load environment variables
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')

# ActiveCampaign fields
fields = {
    '9': 'W4 quantity', 
    '1': 'Bedrijfsnaam', 
    '8': 'K4 quantity', 
    '2': 'In welke producten ben je geïnteresseerd?', 
    '10': 'M4 quantity', 
    '3': 'Waar is het bedrijf gevestigd?', 
    '11': 'Quantity From Sales', 
    '4': 'In welk(e) product(en) ben je geïnteresseerd?', 
    '12': 'Quantity From Orderbump', 
    '5': 'Je bericht', 
    '14': 'B12 quantity', 
    '6': 'Beschrijf je ideale samenwerking*', 
    '15': 'C12 quantity', 
    '7': 'Website', 
    '17': 'F12 quantity', 
    '18': 'P28 quantity', 
    '19': 'S quantity', 
    '20': 'G12 quantity', 
    '13': 'Last Ordered Item(s)', 
    '21': 'Abo'
    }

# Configure WooCommerce API client
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3"
)

# Create response and print
subscription_id = '4889'
initial_response = wcapi.get(f"subscriptions/{subscription_id}")
woocommerce_data = initial_response.json()

# Retrieve email
email = woocommerce_data.get('billing', {}).get('email')

# Retrieve ActiveCampaign contact
url = active_campaign_api_url + "contacts/"
headers = {
    "accept": "application/json",
    "Api-Token": active_campaign_api_token
    }
params = {
        'email': email
    }
response = requests.get(url, headers=headers, params=params)
active_campaign_data = response.json()

# Retrieve ActiveCampaign ID
active_campaign_id = active_campaign_data['contacts'][0]['id']

# Retrieve field values
url = active_campaign_api_url + f"contacts/{active_campaign_id}/fieldValues"
headers = {
    "accept": "application/json",
    "Api-Token": active_campaign_api_token
    }
response = requests.get(url, headers=headers, params=params)
field_values = response.json()

# Extract current values
desired_field = 21
contact_id = None
current_abo_value = None
specific_abo_field_id = None

for item in field_values['fieldValues']:
    if int(item['field']) == desired_field:
        contact_id = item['contact']
        current_abo_value = item['value']
        specific_abo_field_id = item['id']

# Turn abo value into integer
current_abo_value = int(current_abo_value)

# Update abo value
new_abo_value = current_abo_value + 1

# Update field values
url = active_campaign_api_url + f"fieldValues/{specific_abo_field_id}"
headers = {
    "accept": "application/json",
    "Api-Token": active_campaign_api_token
    }
payload = {
    "fieldValue": {
        "contact": f"{contact_id}",
        "field": "21",
        "value": f"{new_abo_value}"
    },
    "useDefaults": False
}
requests.put(url, json=payload, headers=headers)

''' Extract payment method
payment_method = woocommerce_data.get('payment_method_title')
if payment_method in ['iDEAL', 'Bancontact']:
    next_payment_date_str = woocommerce_data.get('next_payment_date_gmt')
    if next_payment_date_str:
        try:
            # Converteer de datum string naar een datetime object
            next_payment_date = datetime.strptime(next_payment_date_str, '%Y-%m-%dT%H:%M:%S')
            new_next_payment_date = next_payment_date - timedelta(days=7)

            # Update WooCommerce subscription
            update_data = {
                "next_payment_date": f"{new_next_payment_date}"
            }

            # Voer de PUT request uit naar WooCommerce API
            response = wcapi.put(f"subscriptions/{subscription_id}", update_data)
            print(response.status_code)

            # Controleer of de PUT request succesvol was (status code 200)
            if response.status_code == 200:
                print("PUT request succesvol uitgevoerd.")
            else:
                print(f"Fout bij het uitvoeren van PUT request: {response.status_code}")
        
        except ValueError as e:
            print(f"Fout bij datum conversie: {e}")
        
        except requests.exceptions.RequestException as e:
            print(f"Fout bij het maken van de HTTP request: {e}")
    
    else:
        print("Fout: next_payment_date_gmt ontbreekt in de data.")

else:
    print("No payment date movement needed")'''