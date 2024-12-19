from dotenv import load_dotenv
import logging
import os

def env_check():
    if os.path.exists('.env'):
            load_dotenv()
            print("Lokaal draaien: .env bestand gevonden en geladen.")
            logging.info("Lokaal draaien: .env bestand gevonden en geladen.")
    else:
        logging.info("Draaien in productieomgeving (Azure): .env bestand niet gevonden.")