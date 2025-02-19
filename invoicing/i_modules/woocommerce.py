
from requests.auth import HTTPBasicAuth
from datetime import datetime
import requests

# Function to get batch data
def get_batch_data(order_id, api_url, username, password):

    endpoint = f"order/{order_id}/batches"
    url = api_url + endpoint
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=120)
        if response.status_code == 200:
            response_data_2 = response.json()
        else: 
            print(f"Fout bij het verwerken van order {order_id}: Statuscode {response.status_code}")
            response_data_2 = {}
    except Exception as e:
        print(f"Fout bij het verwerken van order {order_id}: {str(e)}")
        response_data_2 = {}

    # Extract batch data
    batches = response_data_2.get('BatchLines', [])
    batch_list = []

    for batch_data in batches:
        sku = batch_data.get('Sku', None)
        batch_info = batch_data.get('BatchContent', {})
        title = batch_info.get('Title') if batch_info else None
        if title:
            batch_list.append(title)

    # Create an SKU dictionairy
    batch_sku_dict = {}

    for batch_data in response_data_2.get('BatchLines', []):
        sku = batch_data.get('Sku', None)
        batch_info = batch_data.get('BatchContent')
        title = batch_info.get('Title') if batch_info else None

        if sku and title:
            endpoint = f"product/{sku}"
            url = api_url + endpoint
            try:
                response = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=120)
                if response.status_code == 200:
                    product_data = response.json()
                    product_name = product_data.get('Description', None)
                    if product_name:
                        batch_sku_dict[product_name] = title
            except Exception as e:
                print(f"Fout bij het ophalen van productinformatie voor SKU {sku}: {str(e)}")

    # Maak een kopie van de dictionary
    batch_sku_dict_copy = batch_sku_dict.copy()

    # Itereer over de kopie en update de oorspronkelijke dictionary
    for key, value in batch_sku_dict_copy.items():
        batch_sku_dict[key] = value

    return batch_sku_dict

# Function to extract and print order details
def extract_order_details(order_id, wcapi):
    order_data = wcapi.get(f"orders/{order_id}").json()
    order_id = order_data.get('id', '')
    date_created_iso = order_data.get('date_created', '')
    if date_created_iso:
        date_created_obj = datetime.fromisoformat(date_created_iso)
        date_created = date_created_obj.strftime('%d-%m-%Y')
    else:
        date_created = ''
    company = order_data.get('billing', {}).get('company', '').title()
    first_name = order_data.get('billing', {}).get('first_name', '')
    last_name = order_data.get('billing', {}).get('last_name', '')
    name = f"{first_name.title()} {last_name.title()}" 
    address = order_data.get('billing', {}).get('address_1', '').title()
    postal_code = order_data.get('billing', {}).get('postcode', '')
    city = order_data.get('billing', {}).get('city', '').title()
    country_code = order_data.get('billing', {}).get('country', '')
    if country_code == 'NL':
        country_name = 'Nederland'
    elif country_code == 'BE':
        country_name = 'België'
    else:
        country_name = country_code
    shipping_total = order_data.get('shipping_total', '')
    if country_code == 'NL':
        btw_percentage = 0.09
    elif country_code == 'BE':
        btw_percentage = 0.06
    else:
        btw_percentage = 0.0
    if country_code == 'NL':
        btw = '(9%)'
    elif country_code == 'BE':
        btw = '(6%)'
    else:
        btw = ''
    total_value = order_data.get('total', '')

    product_lines = []
    for i, item in enumerate(order_data.get('line_items', []), 1):
        product_name = item.get('name', '')
        quantity = item.get('quantity', 0)
        product_price = item.get('price', '')
        subtotal = item.get('subtotal', '')
        sku = item.get('sku', '')
        product_name = product_name.capitalize()
        line = f"{i}. Product Naam: {product_name}, Aantal: {quantity}, Productbedrag: {product_price}, Subtotaal Bedrag: {subtotal}, SKU: {sku}"
        product_lines.append(line)

    mail = order_data.get('billing', {}).get('email', '')

    return order_id, date_created, company, name, address, postal_code, city, country_name, shipping_total, btw_percentage, btw, total_value, product_lines, mail, first_name

def get_order_ids(customer_email, start_date, end_date, wcapi):

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
        "before": f"{end_date}T23:59:59",
        "per_page": 100
    }

    # Get orders using pagination
    all_order_ids = []
    page = 1

    while True:
        # Get order response
        params_orders["page"] = page
        order_response = wcapi.get("orders", params=params_orders)
        data = order_response.json()

        # Fallback if there is no data
        if not data:
            break

        order_ids = [item['id'] for item in data]
        all_order_ids.extend(order_ids)
        page += 1

    return all_order_ids
