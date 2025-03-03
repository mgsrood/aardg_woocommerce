#!/usr/bin/env python3
"""
Script om data van BigQuery naar de lokale SQLite database te synchroniseren.
"""

import argparse
import os
import sys
from utils.bigquery import sync_data_from_bigquery
import logging

# Configureer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Synchroniseer data van BigQuery naar lokale SQLite database.')
    parser.add_argument('--force', action='store_true', help='Forceer synchronisatie, zelfs als de database al bestaat')
    args = parser.parse_args()
    
    # Controleer of de database al bestaat
    db_path = os.getenv('SQLITE_DB_PATH', 'klantenservice_applicatie/data/woocommerce.db')
    
    if os.path.exists(db_path) and not args.force:
        logger.info(f"Database bestaat al op {db_path}. Gebruik --force om te overschrijven.")
        return
    
    # Voer synchronisatie uit
    success = sync_data_from_bigquery()
    
    if success:
        logger.info("Synchronisatie succesvol voltooid.")
    else:
        logger.error("Synchronisatie mislukt.")
        sys.exit(1)

if __name__ == "__main__":
    main() 