import requests
import json
import os
from google.cloud import bigquery
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account

# Load .env
load_dotenv()

# Today
today = datetime.today().strftime("%Y-%m-%d")

# Base URL
url = os.environ.get('NOTION_URL')

# Authorization
access_token = os.environ.get('NOTION_ACCESS_TOKEN', '')
headers = {
    "Authorization": "Bearer " + access_token,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}
database_id = os.environ.get('NOTION_DATABASE_ID', '')

# Define Get Data From BigQuery
def get_data_from_bigquery(project_id, dataset_id, table_id):
    
    # Maak een client
    client = bigquery.Client(project=project_id)
    
    # Definieer je query
    query = f"""
        SELECT * 
        FROM `{project_id}.{dataset_id}.{table_id}`
    """
    
    # Voer de query uit
    query_job = client.query(query)
    
    # Wacht op de resultaten
    results = query_job.result()
    
    # Converteer de resultaten naar een DataFrame
    df = results.to_dataframe()
    return df

# Get the GCP keys
gc_keys = os.getenv("AARDG_GOOGLE_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gc_keys

credentials = service_account.Credentials.from_service_account_file(gc_keys)
project_id = credentials.project_id
client = bigquery.Client(credentials=credentials, project=project_id)

# BigQuery information
project_id = os.environ["SUBSCRIPTION_PROJECT_ID"]
dataset_id = os.environ["SUBSCRIPTION_DATASET_ID"]
table_id = os.environ["SUBSCRIPTION_TABLE_ID"]
full_table_id = f'{project_id}.{dataset_id}.{table_id}'

# Get the BigQuery data
dataframe = get_data_from_bigquery(project_id, dataset_id, table_id)

# Writing endpoint for Notion
endpoint = "/pages/"
full_url = url + endpoint

for index, row in dataframe.iterrows():
    # Details of the new rows
    new_row_data = {
        "parent": {"database_id": database_id},
        "properties": {
            "Datum": {"title": [{"text": {"content": str(today)}}]},
            "Abo Producten": {"number": row['total_subscription_products']} if not pd.isna(row['total_subscription_products']) else {"number": 0},
            "Gem. Abo Producten": {"number": row['avg_subscription_quantity']} if not pd.isna(row['avg_subscription_quantity']) else {"number": 0},
            "Totale Abo Waarde": {"number": row['product_total']} if not pd.isna(row['product_total']) else {"number": 0},
            "Gem. Abo Waarde": {"number": row['avg_subscription_value']} if not pd.isna(row['avg_subscription_value']) else {"number": 0},
            "Gem. Product Waarde": {"number": row['avg_product_value']} if not pd.isna(row['avg_product_value']) else {"number": 0},
            "Gem. Verzendkosten": {"number": row['avg_shipping_paid_per_product']} if not pd.isna(row['avg_shipping_paid_per_product']) else {"number": 0},
            "Gem. Frequentie": {"number": row['avg_week_frequency']} if not pd.isna(row['avg_week_frequency']) else {"number": 0},
        }
    }
    
    # Send a POST-request to write new data
    response = requests.post(full_url, headers=headers, json=new_row_data)

    # Check the status
    if response.status_code == 200:
        print(f"Rij {index + 1} succesvol toegevoegd aan de Notion Database.")
    else:
        print(f"Fout bij het toevoegen van rij {index + 1}:", response.text)