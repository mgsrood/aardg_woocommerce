from datetime import datetime, timedelta
import requests
from woocommerce import API

def move_next_payment_date(data, wcapi):
    payment_method = data.get('payment_method_title')
    if payment_method in ['iDEAL', 'Bancontact']:
        next_payment_date_str = data.get('next_payment_date_gmt')
        if next_payment_date_str:
            # Converteer de datum string naar een datetime object
            next_payment_date = datetime.strptime(next_payment_date_str, '%Y-%m-%dT%H:%M:%S')
            new_next_payment_date = next_payment_date - timedelta(days=7)

            # Update WooCommerce subscription
            update_data = {
                "next_payment_date": f"{new_next_payment_date}"
            }

            # Voer de PUT request uit naar WooCommerce API
            wcapi.put(f"subscriptions/{data['id']}", update_data)

def update_ac_abo_field(data, ac_api_url, ac_api_token):
    # Retrieve email
    email = data.get('billing', {}).get('email')

    # Retrieve ActiveCampaign contact
    url = ac_api_url + "contacts/"
    headers = {
        "accept": "application/json",
        "Api-Token": ac_api_token
        }
    params = {
            'email': email
        }
    response = requests.get(url, headers=headers, params=params)
    ac_data = response.json()

    # Retrieve ActiveCampaign ID
    ac_id = ac_data['contacts'][0]['id']

    # Retrieve field values
    url = ac_api_url + f"contacts/{ac_id}/fieldValues"
    headers = {
        "accept": "application/json",
        "Api-Token": ac_api_token
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
    new_abo_value = current_abo_value - 1

    # Update field values
    url = ac_api_url + f"fieldValues/{specific_abo_field_id}"
    headers = {
        "accept": "application/json",
        "Api-Token": ac_api_token
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