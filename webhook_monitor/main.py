from m_modules.webhook_monitor import check_and_reactivate_webhooks
from m_modules.config import determine_script_id
from m_modules.log import end_log, setup_logging
from m_modules.env_tool import env_check
from woocommerce import API
import logging
import time
import os

def main():

    # Check uitvoering: lokaal of productie
    env_check()

    # Algemene configuratie
    klant = "Aard'g"
    script = "Webhook Monitor"
    bron = "WooCommerce"
    start_time = time.time()

    # Webhook namen die we willen monitoren
    required_webhooks = [
        "Order Verwerking",
        "Abonnement Verwerking",
        "Facebook Audience",
        "Product Velden",
        "Product Tags",
        "Abonnements Tag",
        "Abonnements Veld Ophogen",
        "Abonnements Veld Verlagen",
        "Besteldatum"
    ]

    # Woocommerce variabelen
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    
    # Database variabelen
    driver = '{ODBC Driver 18 for SQL Server}'
    username = os.getenv('GEBRUIKERSNAAM')
    database = os.getenv('DATABASE')
    password = os.getenv('PASSWORD')
    server = os.getenv('SERVER')
    greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

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
        check_and_reactivate_webhooks(wcapi, required_webhooks)

    except Exception as e:
        logging.error(f"Script mislukt: {e}")

    # Eindtijd logging
    end_log(start_time)
        
if __name__ == "__main__":
    # Start main
    main()