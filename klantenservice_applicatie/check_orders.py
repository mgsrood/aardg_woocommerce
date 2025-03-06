from google.cloud import bigquery
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def check_bigquery_orders():
    client = bigquery.Client()
    table_ref = os.getenv('BIGQUERY_ORDERS_TABLE_REF')
    
    query = f'''
    SELECT COUNT(*) as count, MIN(date_created) as earliest, MAX(date_created) as latest
    FROM `{table_ref}`
    WHERE date_created >= '2024-03-01'
    '''
    
    query_job = client.query(query)
    results = query_job.result()
    
    logger.info("BigQuery orders deze maand:")
    for row in results:
        logger.info(f'Aantal orders: {row.count}')
        logger.info(f'Eerste order: {row.earliest}')
        logger.info(f'Laatste order: {row.latest}')

def check_sqlite_orders():
    db_path = os.getenv('SQLITE_DB_PATH', 'data/woocommerce.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT COUNT(*) as count, MIN(date_created) as earliest, MAX(date_created) as latest
    FROM orders
    WHERE date_created >= '2024-03-01'
    ''')
    
    row = cursor.fetchone()
    logger.info("\nSQLite orders deze maand:")
    logger.info(f'Aantal orders: {row[0]}')
    logger.info(f'Eerste order: {row[1]}')
    logger.info(f'Laatste order: {row[2]}')
    
    # Laat een paar voorbeelden zien
    cursor.execute('''
    SELECT id, date_created, total, status
    FROM orders
    WHERE date_created >= '2024-03-01'
    ORDER BY date_created DESC
    LIMIT 5
    ''')
    
    logger.info("\nLaatste 5 orders van deze maand:")
    for row in cursor.fetchall():
        logger.info(f'Order {row[0]}: {row[1]} - €{row[2]} - {row[3]}')
    
    conn.close()

if __name__ == "__main__":
    logger.info("Controleren van orders in beide databases...")
    check_bigquery_orders()
    check_sqlite_orders() 