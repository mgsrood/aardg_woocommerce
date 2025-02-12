from env_tool import env_check, determine_base_dir
from config import determine_script_id
from log import setup_logging, end_log
from woocommerce import API
import logging
import time
import json
import os

def main():
    
    # Check uitvoering: lokaal of productie
    env_check()
    
    # Configuratie
    klant = "Aard'g"
    script = "Catalogus"
    bron = "WooCommerce"
    start_time = time.time()

    # Laad omgevingsvariabelen
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    
    # Database variabelen
    driver = '{ODBC Driver 18 for SQL Server}'
    username = os.getenv('GEBRUIKERSNAAM')
    database = os.getenv('DATABASE')
    password = os.getenv('PASSWORD')
    server = os.getenv('SERVER')
    greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)
    
    # Logging instellen
    setup_logging(greit_connection_string, klant, bron, script, script_id)

    # WooCommerce API instellen
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )

    try:
        # Producten ophalen
        products = []
        page = 1
        
        while True:
            # Verkrijg de producten van de huidige pagina
            response = wcapi.get("products", params={"page": page, "per_page": 100})
            
            # Response controleren
            if response.status_code != 200:
                logging.error(f"Fout bij het ophalen van pagina {page}: {response.status_code}")
                break
            else:
                page_products = response.json()
                
                # Als er geen producten zijn, stoppen we
                if not page_products:
                    break
                
                # Voeg de producten van deze pagina toe aan de lijst
                products.extend(page_products)
                
                # Ga naar de volgende pagina
                page += 1
        
        # Product catalogus dictioniary maken
        product_catalogue = {
        }
        
        # Producten toevoegen aan catalogus
        for product in products:
            product_id = product['id']
            product_sku = product['sku']
            product_catalogue[product_sku] = product_id

        # Opslaan in JSON bestand
        base_dir = determine_base_dir()
        file_path = os.path.join(base_dir, 'projecten', 'woocommerce', 'webhooks', 'data', 'product_catalog.json')

        with open(file_path, 'w') as json_file:
            json.dump(product_catalogue, json_file, indent=4)
        logging.info(f"Product catalogus opgeslagen als JSON bestand: {file_path}")

    except Exception as e:
        logging.error(f"Er is een fout opgetreden: {e}")
    
    # Eindtijd logging
    end_log(start_time)

if __name__ == '__main__':
    main()