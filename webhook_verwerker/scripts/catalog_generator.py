from dotenv import load_dotenv
from woocommerce import API
import logging
import time
import json
import os

def main():
    # Basis logging configuratie
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    load_dotenv()
    
    # Configuratie
    klant = "Aard'g"
    script = "CatalogusGenerator"
    bron = "WooCommerce"
    start_time = time.time()

    logging.info(f"Start {script} voor {klant} vanuit {bron}.")

    # Laad omgevingsvariabelen
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    
    if not all([woocommerce_url, consumer_key, consumer_secret]):
        logging.error("Ontbrekende WooCommerce API credentials of URL. Controleer environment variables.")
        return

    # WooCommerce API instellen
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )

    try:
        logging.info("Start ophalen producten van WooCommerce...")
        # Producten ophalen
        products = []
        page = 1
        
        while True:
            # Verkrijg de producten van de huidige pagina
            response = wcapi.get("products", params={"page": page, "per_page": 100})
            
            # Response controleren
            if response.status_code != 200:
                logging.error(f"Fout bij het ophalen van producten pagina {page}: {response.status_code} - {response.text}")
                break
            else:
                page_products = response.json()
                
                if not page_products:
                    logging.info(f"Geen producten meer gevonden op pagina {page}. Totaal {len(products)} producten tot nu toe.")
                    break
                
                products.extend(page_products)
                logging.info(f"Pagina {page} succesvol opgehaald, {len(page_products)} producten. Totaal nu: {len(products)}.")
                page += 1
        
        logging.info(f"Totaal {len(products)} producten opgehaald van WooCommerce.")
        # Product catalogus dictioniary maken
        product_catalogue = {
        }
        
        # Producten toevoegen aan catalogus
        for product in products:
            product_id = product['id']
            product_sku = product['sku']
            if product_sku: 
                product_catalogue[product_sku] = product_id
            else:
                logging.warning(f"Product met ID {product_id} ('{product.get('name', 'N/A')}') heeft een lege SKU en wordt overgeslagen.")

        # Opslaan in JSON bestand
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_script_dir, '..', 'data', 'product_catalog.json')
        file_path = os.path.normpath(file_path)

        with open(file_path, 'w') as json_file:
            json.dump(product_catalogue, json_file, indent=4)
        logging.info(f"Product catalogus succesvol opgeslagen in: {file_path}")

    except Exception as e:
        logging.error(f"Er is een fout opgetreden tijdens het genereren van de catalogus: {e}", exc_info=True)
    
    # Eindtijd logging
    logging.info(f"{script} voltooid in {time.time() - start_time:.2f} seconden.")

if __name__ == '__main__':
    main()