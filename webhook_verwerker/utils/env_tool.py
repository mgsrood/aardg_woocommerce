from dotenv import load_dotenv
import logging
import os

def determine_base_dir():
    """
    Bepaalt de basis directory voor het .env bestand op basis van het platform.
    
    Returns:
        str: Het pad naar de basis directory
    """
    if "Users" in os.path.expanduser("~"):  # Voor MacBook
        return "/Users/maxrood/werk/greit/klanten/aardg/"
    else:  # Voor VM
        return "/home/maxrood/aardg/"

def env_check():
    """
    Laadt environment variabelen uit het juiste .env bestand.
    Zoekt eerst naar .env in de basis directory, valt terug op standaard gedrag.
    """
    base_dir = determine_base_dir()
    env_path = os.path.join(base_dir, '.env')
    
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"Environment bestand geladen van: {env_path}")
        logging.info(f"Environment bestand geladen van: {env_path}")
        return True
    else:
        load_dotenv()  # Fallback naar standaard gedrag
        print("Standaard environment loading gebruikt")
        logging.info("Standaard environment loading gebruikt")
        return False