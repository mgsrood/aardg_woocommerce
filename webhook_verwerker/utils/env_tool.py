from dotenv import load_dotenv
import logging
import os

def determine_base_dir():
    if "Users" in os.path.expanduser("~"):  # Specifiek voor je MacBook
            return "/Users/maxrood/werk/greit/klanten/aardg/"
    else:  # Voor je VM
        return "/home/maxrood/aardg/"

def check_required_env_vars():
    """Controleert of alle vereiste environment variables aanwezig zijn."""
    required_vars = [
        'SECRET_KEY',
        'ACTIVE_CAMPAIGN_API_URL',
        'ACTIVE_CAMPAIGN_API_TOKEN',
        'WOOCOMMERCE_CONSUMER_KEY',
        'WOOCOMMERCE_CONSUMER_SECRET',
        'WOOCOMMERCE_URL',
        'GEBRUIKERSNAAM',
        'DATABASE',
        'PASSWORD',
        'SERVER'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Ontbrekende environment variables: {', '.join(missing_vars)}")
    
    logging.info("Alle vereiste environment variables zijn aanwezig.")

def env_check():
    base_dir = determine_base_dir()
    env_path = os.path.join(base_dir, '.env')
    
    if os.path.exists(env_path):
        load_dotenv()
        logging.info("Lokaal draaien: .env bestand gevonden en geladen.")
    else:
        logging.info("Draaien in productieomgeving: .env bestand niet gevonden.")
    
    # Controleer vereiste environment variables
    check_required_env_vars()