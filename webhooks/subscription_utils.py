from datetime import datetime, timedelta
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

def change_first_name(data, wcapi):
    data['billing']['first_name'] = "Mia"
    
    # Update WooCommerce subscription
    update_data = {
        'billing': {
            'first_name': data['billing']['first_name']
        }
    }
    wcapi.put(f"subscriptions/{data['id']}", update_data)