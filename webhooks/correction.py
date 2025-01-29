from modules.wc_functions import update_or_insert_order_to_bigquery
from modules.env_tool import env_check
from datetime import datetime, timedelta
from woocommerce import API
import os

def main():

    # Check uitvoering: lokaal of productie
    env_check()

    # Woocommerce variabelen
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    secret_key = os.getenv('SECRET_KEY')

    # Google variabelen
    credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    # Database variabelen
    driver = '{ODBC Driver 18 for SQL Server}'
    username = os.getenv('GEBRUIKERSNAAM')
    database = os.getenv('DATABASE')
    password = os.getenv('PASSWORD')
    server = os.getenv('SERVER')
    greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

    # Algemene configuratie
    bron = "WooCommerce"
    klant = "Aard'g"
    route_naam = "Correctie"
    script_id = 1

    # WooCommerce API configuratie
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )

    # Ophalen WooCommerce orders
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    all_orders = []
    page = 1

    while True:
        response = wcapi.get("orders", params={
            "status": "completed",
            "after": seven_days_ago,
            "per_page": 100,
            "page": page
        }).json()

        if not response:  # Stop als er geen resultaten meer zijn
            break

        all_orders.extend(response)
        page += 1

    print(f"Opgehaalde orders: {len(all_orders)}")
    
    # Order ids
    for order in all_orders:
        order_id = order["id"]
        update_or_insert_order_to_bigquery(greit_connection_string, klant, script_id, route_naam, order_id, wcapi)
        
if __name__ == "__main__":
    main()