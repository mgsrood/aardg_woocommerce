from google.cloud import bigquery
import os
from dotenv import load_dotenv

load_dotenv()

# Stel je Google Cloud credentials in als deze nog niet zijn ingesteld
credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
print(credentials_path)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

# Initialiseer de BigQuery client
client = bigquery.Client()

# Verwijs naar de dataset en tabel waarin je de gegevens wilt invoegen
dataset_id = os.getenv('DATASET_ID')
table_id = os.getenv('TABLE_ID')

# Bouw de volledige tabelreferentie
table_ref = client.dataset(dataset_id).table(table_id)

# Verkrijg de tabel om ervoor te zorgen dat deze bestaat en dat je schema correct is
try:
    table = client.get_table(table_ref)
    print(f"Table {table_id} in dataset {dataset_id} accessed successfully.")
except Exception as e:
    print(f"Error accessing table: {e}")
    exit(1)

# Maak een eenvoudig testlog-item dat overeenkomt met het schema van je BigQuery-tabel
test_log_entry = [{
    "timestamp": "2024-08-30 08:27:43",
    "log_level": "INFO",
    "message": "Test log entry"
}]

# Probeer de invoeging
try:
    errors = client.insert_rows_json(table, test_log_entry)
    if errors:
        print(f"Errors occurred while inserting: {errors}")
    else:
        print("Insert successful")
except Exception as e:
    print(f"An error occurred during the insert operation: {e}")
