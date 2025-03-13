from c_modules.wc_functions import update_or_insert_sub_to_bigquery
from c_modules.config import determine_script_id
from c_modules.log import end_log, setup_logging
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
    script = "Abonnement Correctie"
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
        all_subscriptions = []
        subscription_count = 0
        page = 1

        while True:
            try:
                response = wcapi.get("subscriptions", params={
                    "per_page": 100,
                    "page": page
                }).json()

                if not response:  # Stop als er geen resultaten meer zijn
                    break

                all_subscriptions.extend(response)
                page += 1
                subscription_count += len(response)
                logging.info(f"Opgehaald: {subscription_count} abonnementen")
                
            except Exception as e:
                logging.error(f"Fout bij ophalen pagina {page}: {str(e)}")
                break
            
        logging.info(f"Totaal opgehaalde abonnementen: {len(all_subscriptions)}")
    
        if all_subscriptions:
            # Verzamel alle subscription IDs
            subscription_ids = [subscription["id"] for subscription in all_subscriptions]
            
            # Verwerk alle subscriptions in batches
            update_or_insert_sub_to_bigquery(subscription_ids, wcapi)
        else:
            logging.warning("Geen abonnementen gevonden om te verwerken")
    
    except Exception as e:
        logging.error(f"Script mislukt: {e}")

    # Eindtijd logging
    end_log(start_time)
        
if __name__ == "__main__":
    main()