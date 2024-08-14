from woocommerce import API
from dotenv import load_dotenv
import os
import json

load_dotenv()

# Load environment variables
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')

# Configuring the WooCommerce API
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3",
    timeout=60
)

def retrieve_all_products(wcapi, per_page=100):
    products = []
    page = 1
    
    while True:
        # Verkrijg de producten van de huidige pagina
        response = wcapi.get("products", params={"page": page, "per_page": per_page})
        page_products = response.json()
        
        # Als er geen producten zijn, stoppen we
        if not page_products:
            break
        
        # Voeg de producten van deze pagina toe aan de lijst
        products.extend(page_products)
        
        # Ga naar de volgende pagina
        page += 1
    
    product_catalogue = {
    }
    for product in products:
        product_id = product['id']
        product_sku = product['sku']
        product_catalogue[product_sku] = product_id

    return product_catalogue

def save_catalogue_to_json(catalogue, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(catalogue, json_file, indent=4)
    print(f"Product catalogus opgeslagen als JSON bestand: {file_path}")

if __name__ == '__main__':
    # Catalogus ophalen
    catalogue = retrieve_all_products(wcapi)

    # Catalogus lokaal opslaan
    output_path = os.path.join(os.path.dirname(__file__), '../data/product_catalog.json')
    save_catalogue_to_json(catalogue, output_path)