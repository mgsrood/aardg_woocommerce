from utils.request_check import validate_signature, parse_request_data
from utils.log import start_log, end_log, setup_logging
from utils.config import get_and_use_next_script_id
from flask import request, jsonify
from functools import wraps
import logging
import random
import time
import os

# Default connection string
DEFAULT_CONN_STR = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.getenv('SERVER')};DATABASE={os.getenv('DATABASE')};UID={os.getenv('GEBRUIKERSNAAM')};PWD={os.getenv('PASSWORD')}"

class RouteConfig:
    """Configuratie object voor route initialisatie"""
    def __init__(self, 
                 verify_signature=False,
                 parse_data=True,
                 secret_key=None,
                 retry_config=None):
        self.verify_signature = verify_signature
        self.parse_data = parse_data
        self.secret_key = secret_key
        self.retry_config = retry_config or {
            'max_retries': 5,
            'initial_backoff': 5,
            'max_backoff': 300
        }



def initialize_route(config: RouteConfig, bron: str, script: str = 'Webhook Verwerking', conn_str: str = DEFAULT_CONN_STR, process_func=None):
    """
    Route decorator die een route initialiseert met gestandaardiseerde stappen.
    
    Args:
        config: RouteConfig object met de gewenste validatie opties
        bron: De bron van de webhook (bijv. "WooCommerce", "Active Campaign")
        script: De naam van het script (standaard "Webhook Verwerking")
        conn_str: Database connection string (standaard greit_connection_string)
        process_func: De functie die de data moet verwerken
    """
    if process_func is None:
        raise ValueError("Process functie is verplicht")
        
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Configureer logging voor deze route
            setup_logging(
                conn_str=conn_str,
                klant="Aardg",
                bron=bron,
                script=script
            )
            
            # Start logging
            start_time = start_log()
            
            retry_count = 0
            while True:
                try:
                    # Genereer script_id
                    script_id = get_and_use_next_script_id(
                        connection_string=conn_str,
                        bron=bron,
                        script_naam=script
                    )
                    request.script_id = script_id
                    
                    # Signature validatie indien nodig
                    if config.verify_signature:
                        if not config.secret_key:
                            raise ValueError("Signature verificatie gevraagd maar geen secret opgegeven")
                        
                        if not validate_signature(request, config.secret_key):
                            raise PermissionError("Ongeldige signature")
                            
                        logging.info("Signature gevalideerd")
                    
                    # Data parsing indien nodig
                    if config.parse_data:
                        data = parse_request_data()
                        if not data:
                            raise ValueError("Kon geen geldige data uit de request halen")
                    else:
                        data = request.get_json()
                    
                    # Voer de process functie uit met de data
                    resultaat = process_func(data)
            
                    # Geef het resultaat terug
                    return jsonify({
                        "message": "Webhook verwerkt",
                        "script_id": script_id,
                        "resultaat": resultaat
                    })
                    
                except ValueError as e:
                    error_msg = str(e)
                    logging.error(f"Validatie fout: {error_msg}")
                    
                    return jsonify({
                        "error": error_msg,
                        "script_id": getattr(request, 'script_id', None)
                    }), 400
                    
                except PermissionError as e:
                    error_msg = str(e)
                    logging.error(f"Authenticatie fout: {error_msg}")
                    

                    
                    return jsonify({
                        "error": error_msg,
                        "script_id": getattr(request, 'script_id', None)
                    }), 401
                    
                except Exception as e:
                    error_msg = str(e)
                    if retry_count == config.retry_config['max_retries']:
                        logging.error(f"Maximaal aantal pogingen ({config.retry_config['max_retries']}) bereikt voor route {request.path}")
                     
                        return jsonify({
                            "error": "Service tijdelijk niet beschikbaar. Probeer het later opnieuw.",
                            "script_id": getattr(request, 'script_id', None)
                        }), 503

                    # Bereken wachttijd met exponentiële backoff en jitter
                    sleep_time = min(
                        config.retry_config['initial_backoff'] * (2 ** retry_count) + random.uniform(0, 1),
                        config.retry_config['max_backoff']
                    )
                    
                    logging.warning(f"Poging {retry_count + 1}/{config.retry_config['max_retries']} mislukt voor route {request.path}. "
                                  f"Wacht {sleep_time:.2f} seconden voor volgende poging. Fout: {error_msg}")
                    
                    time.sleep(sleep_time)
                    retry_count += 1
                finally:
                    # Eind logging
                    end_log(start_time)
                
        return wrapper
    return decorator 