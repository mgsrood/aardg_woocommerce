#!/bin/bash

# Installeer benodigde packages voor BigQuery
pip install -r requirements-bigquery.txt

# Stel omgevingsvariabelen in
export USE_SQLITE=true
export SQLITE_DB_PATH="data/woocommerce.db"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"

# Importeer margegegevens uit BigQuery
echo "Importeren van margegegevens uit BigQuery..."
python import_bigquery_data.py

# Start de applicatie
echo "Starten van de applicatie..."
python app.py 