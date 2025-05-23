from c_modules.wc_functions import update_or_insert_order_to_bigquery
from c_modules.config import determine_script_id
from c_modules.log import end_log, setup_logging
from datetime import datetime, timedelta
from c_modules.env_tool import env_check
from woocommerce import API
import logging
import time
import os

def main():

    # Check uitvoering: lokaal of productie
    env_check()

    # Woocommerce variabelen
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')

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
    klant = "Aard'g"
    script = "Order Correctie"
    bron = "WooCommerce"
    start_time = time.time()

    # WooCommerce API configuratie
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )

    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)

    # Set up logging (met database logging)
    setup_logging(greit_connection_string, klant, bron, script, script_id)

    try:
        # Ophalen WooCommerce orders
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        all_orders = []
        page = 1

        while True:
            response = wcapi.get("orders", params={
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
            update_or_insert_order_to_bigquery(order_id, wcapi)
    
    except Exception as e:
        logging.error(f"Script mislukt: {e}")

    # Eindtijd logging
    end_log(start_time)
        
if __name__ == "__main__":
    main()