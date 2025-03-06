from google.cloud import bigquery
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def check_table_schema():
    client = bigquery.Client()
    table_ref = os.getenv('BIGQUERY_ORDERS_TABLE_REF')
    
    # Get the table
    table = client.get_table(table_ref)
    
    # Print the schema
    logger.info("BigQuery orders tabel schema:")
    for field in table.schema:
        logger.info(f'{field.name}: {field.field_type}')

if __name__ == "__main__":
    check_table_schema() 