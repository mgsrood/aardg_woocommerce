from google.cloud import bigquery
import os
import sqlite3
from dotenv import load_dotenv
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

def check_sqlite_data():
    db_path = os.getenv('SQLITE_DB_PATH', 'data/woocommerce.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check orders
    logger.info("\nLaatste 5 orders:")
    cursor.execute('''
    SELECT id, created_date, completed_date, total, status_display, line_items
    FROM orders
    ORDER BY created_date DESC
    LIMIT 5
    ''')
    
    for row in cursor.fetchall():
        logger.info(f'Order {row[0]}:')
        logger.info(f'  Aangemaakt: {row[1]}')
        logger.info(f'  Afgerond: {row[2]}')
        logger.info(f'  Totaal: €{row[3]}')
        logger.info(f'  Status: {row[4]}')
        logger.info(f'  Producten: {row[5]}')
        logger.info('---')
    
    # Check subscriptions
    logger.info("\nLaatste 5 abonnementen:")
    cursor.execute('''
    SELECT id, date_created, total, status_display, frequency
    FROM subscriptions
    ORDER BY date_created DESC
    LIMIT 5
    ''')
    
    for row in cursor.fetchall():
        logger.info(f'Abonnement {row[0]}:')
        logger.info(f'  Aangemaakt: {row[1]}')
        logger.info(f'  Totaal: €{row[2] if row[2] is not None else "N/A"}')
        logger.info(f'  Status: {row[3]}')
        logger.info(f'  Frequentie: {row[4]}')
        logger.info('---')
    
    conn.close()

if __name__ == "__main__":
    check_sqlite_data() 