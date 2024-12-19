from dotenv import load_dotenv
import os
from woocommerce import API
import json
from google.cloud import bigquery
import logging
from modules.woocommerce_utils import process_order

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Load variables
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')

# Stel je Google Cloud credentials in als deze nog niet zijn ingesteld
credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
print(credentials_path)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

# Initialiseer de BigQuery client
client = bigquery.Client()

# Verwijs naar de dataset en tabel waarin je de gegevens wilt invoegen
dataset_id = "woocommerce_data"
table_id = "orders"

# Bouw de volledige tabelreferentie
table_ref = client.dataset(dataset_id).table(table_id)

# Verkrijg de tabel om ervoor te zorgen dat deze bestaat en dat je schema correct is
try:
    table = client.get_table(table_ref)
    print(f"Table {table_id} in dataset {dataset_id} accessed successfully.")
except Exception as e:
    print(f"Error accessing table: {e}")
    exit(1)

# WCAPI
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3",
    timeout=60
)

# Get Subscription Data
order_id = 105146

try:
    result_message = process_order(order_id, wcapi, client, dataset_id, table_id)
    print(result_message)
except Exception as e:
    print(f"Error processing order: {e}")

