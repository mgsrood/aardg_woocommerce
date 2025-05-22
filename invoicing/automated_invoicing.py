from i_modules.config import determine_script_id, get_first_and_last_day_of_last_month
from i_modules.email import send_email_with_attachment
from i_modules.log import end_log, setup_logging
from i_modules.woocommerce import get_order_ids
from i_modules.generator import single_invoice
from i_modules.env_tool import env_check
from woocommerce import API
import logging
import time
import os

def main():

    # Check uitvoering: lokaal of productie
    env_check()

    # Algemene configuratie
    klant = "Aard'g"
    script = "Factuur"
    bron = "WooCommerce"
    start_time = time.time()

    # Woocommerce variabelen
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')

    # Define the Woocommerce API
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=10
    )

    # Define the Monta API variables
    monta_api_url = os.environ.get('MONTA_API_URL')
    monta_username = os.environ.get('MONTA_USERNAME')
    monta_password = os.environ.get('MONTA_PASSWORD')

    # Database variabelen
    driver = '{ODBC Driver 18 for SQL Server}'
    username = os.getenv('GEBRUIKERSNAAM')
    database = os.getenv('DATABASE')
    password = os.getenv('PASSWORD')
    server = os.getenv('SERVER')
    greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

    # Email configuratie
    order_email = os.environ.get('ORDER_EMAIL')
    invoice_email = os.environ.get('INVOICE_EMAIL')

    if not order_email or not invoice_email:
        error_msg = "De environment variabelen ORDER_EMAIL en INVOICE_EMAIL moeten beide ingesteld zijn."
        logging.error(error_msg)
        raise ValueError(error_msg)
        
    smtp_server = os.environ.get('MAIL_SMTP_SERVER')
    smtp_port = os.environ.get('MAIL_SMTP_PORT')
    sender_email = os.environ.get('MAIL_SENDER_EMAIL')
    sender_password = os.environ.get('MAIL_SENDER_PASSWORD')
    
    # Logo variables
    logo = os.getenv('IMAGE_PATH')

    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)

    # Set up logging (met database logging)
    setup_logging(greit_connection_string, klant, bron, script, script_id)

    try:
        # Begin en einddatum bepalen
        start_date, end_date = get_first_and_last_day_of_last_month()
        
        # Order IDs ophalen
        order_ids = get_order_ids(order_email, start_date, end_date, wcapi)
        
        # Facturen genereren
        all_invoices, order_details = single_invoice(order_ids, monta_api_url, monta_username, monta_password, wcapi, logo)

        # Facturen versturen
        send_email_with_attachment(all_invoices, invoice_email, order_details, smtp_server, smtp_port, sender_email, sender_password)
        
    except Exception as e:
        logging.error(f"Error: {e}")
        
    # Eindtijd logging
    end_log(start_time)
        
if __name__ == "__main__":
    # Start main
    main()