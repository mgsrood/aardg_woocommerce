#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Voeg de huidige directory toe aan het pad zodat we modules kunnen importeren
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configureer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Laad environment variables
load_dotenv()

def main():
    """
    Hoofdfunctie voor het importeren van BigQuery data.
    """
    parser = argparse.ArgumentParser(description='Importeer gegevens uit BigQuery naar SQLite')
    parser.add_argument('--table', type=str, default='order_margin_data', 
                        help='Naam van de tabel om te importeren (standaard: order_margin_data)')
    args = parser.parse_args()
    
    if args.table == 'order_margin_data':
        from klantenservice_applicatie.utils.bigquery_import import import_order_margin_data
        logger.info("Start import van order_margin_data uit BigQuery...")
        result = import_order_margin_data()
        
        if result.get("success"):
            logger.info(f"Import succesvol: {result.get('message')}")
            return 0
        else:
            logger.error(f"Import mislukt: {result.get('error')}")
            return 1
    else:
        logger.error(f"Onbekende tabel: {args.table}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 