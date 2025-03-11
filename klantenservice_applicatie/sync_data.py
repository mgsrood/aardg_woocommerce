#!/usr/bin/env python3
"""
Script om data van BigQuery naar de lokale SQLite database te synchroniseren.
"""

import os
import sys
from utils.bigquery import sync_data_from_bigquery
import logging

# Configureer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Voer synchronisatie uit
    success = sync_data_from_bigquery()
    
    if success:
        logger.info("Synchronisatie succesvol voltooid.")
    else:
        logger.error("Synchronisatie mislukt.")
        sys.exit(1)

if __name__ == "__main__":
    main() 