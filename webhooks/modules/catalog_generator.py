from woocommerce import API
from dotenv import load_dotenv
import os
import json
import pandas as pd
from product_utils import determine_base_product
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe

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

    return product_catalogue, products

def save_catalogue_to_json(catalogue, file_path):
    with open(file_path, 'w') as json_file:
        json.dump(catalogue, json_file, indent=4)
    print(f"Product catalogus opgeslagen als JSON bestand: {file_path}")

def save_catalogue_to_dataframe(products):
    # Maak een DataFrame
    df = pd.json_normalize(products)

    # Selecteer de gewenste kolommen
    selected_columns = [
        'id', 
        'name', 
        'date_created', 
        'date_modified', 
        'sku', 
        'price', 
        'regular_price', 
        'sale_price', 
        'purchasable', 
        'categories'
    ]

    df_selected = df[selected_columns]

    # De categorie namen extraheren
    df_selected['category_names'] = df_selected['categories'].apply(lambda x: [category['name'] for category in x] if x else [])

    # Verwijder de originele 'categories' kolom, aangezien je nu de 'category_name' kolom hebt
    df_selected = df_selected.drop(columns=['categories'])

    # Resultaat tonen
    return df_selected

def write_dataframe_to_google_sheet(credentials_path, spreadsheet_id, sheet_name, spreadsheet_name, df):
    # Verbind met Google Sheets API
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    client = gspread.authorize(creds)

    # Open de Google Sheet 
    spreadsheet = client.open_by_key(spreadsheet_id)

    # Selecteer het werkblad waar je de data wilt schrijven 
    worksheet = spreadsheet.worksheet(f"{spreadsheet_name}")

    # Schrijf de dataframe naar het werkblad
    set_with_dataframe(worksheet, df)

    print(f"Data succesvol toegevoegd aan de Google Sheet: {sheet_name}")

if __name__ == '__main__':
    # Change directory
    os.chdir('/home/maxrood/codering/aardg/projecten/woocommerce/webhooks/modules')
    
    # Catalogus ophalen
    product_catalogue, products = retrieve_all_products(wcapi)

    # Catalogus opslaan als json
    save_catalogue_to_json(product_catalogue, '../data/product_catalog.json')

    # Catalogus dataframe maken
    df = save_catalogue_to_dataframe(products)

    # Add baseproduct column
    df['base_product'] = df['sku'].apply(determine_base_product)

    # Show all columns DataFrame
    pd.set_option('display.max_columns', None)

    # Print DataFrame
    print(df)

    # Google Sheets variabelen
    credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
    sheet_name = os.getenv('SHEET_NAME')
    spreadsheet_name = os.getenv('SPREADSHEET_NAME')
    spreadsheet_id = os.getenv('SPREADSHEET_ID')

    # Write dataframe to Google Sheet
    write_dataframe_to_google_sheet(credentials_path, spreadsheet_id, sheet_name, spreadsheet_name, df)
