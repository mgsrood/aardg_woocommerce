from functools import wraps
from flask import request, jsonify
import logging
from utils.request_check import validate_signature, parse_request_data
from utils.log import start_log, end_log, setup_logging
from utils.config import get_and_use_next_script_id
import os

print("SERVER =", os.getenv("SERVER"))
print("DATABASE =", os.getenv("DATABASE"))
print("GEBRUIKERSNAAM =", os.getenv("GEBRUIKERSNAAM"))
print("PASSWORD =", os.getenv("PASSWORD"))

# Default connection string
DEFAULT_CONN_STR = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={os.getenv('SERVER')};DATABASE={os.getenv('DATABASE')};UID={os.getenv('GEBRUIKERSNAAM')};PWD={os.getenv('PASSWORD')}"

class RouteConfig:
    """Configuratie object voor route initialisatie"""
    def __init__(self, 
                 verify_signature=False,
                 parse_data=True,
                 secret_key=None):
        self.verify_signature = verify_signature
        self.parse_data = parse_data
        self.secret_key = secret_key

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
                logging.error(f"Validatie fout: {str(e)}")
                return jsonify({
                    "error": str(e),
                    "script_id": request.script_id
                }), 400
            except PermissionError as e:
                logging.error(f"Authenticatie fout: {str(e)}")
                return jsonify({
                    "error": str(e),
                    "script_id": request.script_id
                }), 401
            except Exception as e:
                logging.error(f"Fout bij verwerken webhook: {str(e)}")
                return jsonify({
                    "error": "Er ging iets mis bij het verwerken van de webhook",
                    "script_id": request.script_id
                }), 500
            finally:
                # Eind logging
                end_log(start_time)
                
        return wrapper
    return decorator 