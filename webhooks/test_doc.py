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
data = initial_response.json()

# Extract payment method
payment_method = data.get('payment_method_title')
if payment_method in ['iDEAL', 'Bancontact']:
    next_payment_date_str = data.get('next_payment_date_gmt')
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
    print("No payment date movement needed")