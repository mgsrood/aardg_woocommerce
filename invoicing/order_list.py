import json
from woocommerce import API
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load the .env
load_dotenv()

# Define function to retrieve order ids
def order_ids(customer_email, start_date, end_date):

    # Define the WooCommerce API variables
    wcapi = API(
        url = os.environ.get('WOOCOMMERCE_URL'),
        consumer_key=os.environ.get('WOOCOMMERCE_CONSUMER_KEY'),
        consumer_secret=os.environ.get('WOOCOMMERCE_CONSUMER_SECRET'),
        version="wc/v3",
        timeout=10
    )

    # Define params if email is linked to a customer
    params_customer = {
        f"role": "customer",
        "email": {customer_email}
    }

    # Get customer response
    customer_response = wcapi.get("customers", params=params_customer)

    # Check if response resulted in information
    if customer_response.json() == []:
        
        # Define params if email is linked to a subscriber
        params_subscriber = {
        f"role": "subscriber",
        "email": {customer_email}
        }   

        # Get subscriber response
        subscriber_response = wcapi.get("customers", params=params_subscriber)
        subscriber_data = subscriber_response.json()
        
        # Get customer id (from subscriber)
        customer_id = subscriber_data[0]['id']

    # Use customer response
    else: 
        customer_data = customer_response.json()
        
        # Get customer id 
        customer_id = customer_data[0]['id']

    # Define order params
    params_orders = {
        "status": "completed",
        "customer": {customer_id},
        "after": f"{start_date}T00:00:00",
        "before": f"{end_date}T23:59:59"
    }

    # Get order response
    order_response = wcapi.get("orders", params=params_orders)
    data = order_response.json()

    # Fallback if there is no data
    if not data:
            # If no orders found, print a message
            print(f"Geen orders gevonden voor {customer_email} in de specifieke periode.")
            return []

    # Create order id list
    order_ids = [item['id'] for item in data]

    return order_ids

if __name__ == "__main__":
    # Get the environment variabels
    customer_email = os.getenv('MAIL', 'kvloeberghs@gmail.com')
    start_date = os.getenv('START', '2024-01-01')
    end_date = os.getenv('END', '2024-05-01')

    # Use the function to get the order ids
    orders = order_ids(customer_email, start_date, end_date)

    # Remove the spaces from the orders
    orders_str = ', '.join(map(str, orders))

    # Print the orders
    print("Orders:", orders_str)