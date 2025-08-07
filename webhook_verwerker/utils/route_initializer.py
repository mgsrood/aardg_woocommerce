from utils.request_check import validate_signature, parse_request_data
from utils.log import start_log, end_log, setup_logging
from utils.config import get_and_use_next_script_id
from flask import request, jsonify
from functools import wraps
from google.cloud import bigquery
import logging
import os
import time
import random
import json
import hashlib

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

def log_to_bigquery(route, source, script_name, status, message, processing_time_ms, request_id, payload, error_details, retry_count):
    """
    Logt de route verwerking naar BigQuery.
    """
    try:
        # Check of BigQuery logging uitgeschakeld is voor tests
        if os.getenv('SKIP_BIGQUERY_LOGGING', '').lower() in ['true', '1', 'yes']:
            logging.info("BigQuery logging overgeslagen (SKIP_BIGQUERY_LOGGING=true)")
            return
            
        # Check of BigQuery credentials beschikbaar zijn
        credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
        if not credentials_path:
            logging.warning("AARDG_GOOGLE_CREDENTIALS niet ingesteld - BigQuery logging overgeslagen")
            return
            
        # Check of credentials bestand bestaat
        if not os.path.exists(credentials_path):
            logging.warning(f"Google Cloud credentials bestand niet gevonden: {credentials_path}")
            return
            
        # Stel credentials in
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        client = bigquery.Client()
        table_id = "webhook_verwerker.route_processing_logs"
        
        # Hash de payload voor privacy
        hashed_payload = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest() if payload else None
        
        # Extra informatie uit payload halen
        order_id = payload.get('id') if payload else None
        subscription_id = payload.get('id') if payload else None
        billing_email = payload.get('billing', {}).get('email') if payload else None
        first_name = payload.get('billing', {}).get('first_name') if payload else None
        last_name = payload.get('billing', {}).get('last_name') if payload else None
        
        # Bereid de rij voor
        row = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "route": route,
            "source": source,
            "script_name": script_name,
            "status": status,
            "message": message,
            "processing_time_ms": processing_time_ms,
            "request_id": request_id,
            "payload": hashed_payload,
            "error_details": error_details,
            "retry_count": retry_count,
            "environment": os.getenv('ENVIRONMENT', 'development'),
            # Nieuwe velden
            "order_id": order_id,
            "subscription_id": subscription_id,
            "billing_email": billing_email,
            "first_name": first_name,
            "last_name": last_name
        }
        
        # Voeg de rij toe aan BigQuery
        errors = client.insert_rows_json(table_id, [row])
        if errors:
            logging.error(f"Fout bij loggen naar BigQuery: {errors}")
            
    except Exception as e:
        logging.error(f"Fout bij loggen naar BigQuery: {str(e)}")

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
                    
                    # Log succes naar BigQuery
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    log_to_bigquery(
                        route=request.path,
                        source=bron,
                        script_name=script,
                        status="succes",
                        message="Webhook succesvol verwerkt",
                        processing_time_ms=processing_time_ms,
                        request_id=script_id,
                        payload=data,
                        error_details=None,
                        retry_count=retry_count
                    )
                    
                    # Geef het resultaat terug
                    return jsonify({
                        "message": "Webhook verwerkt",
                        "script_id": script_id,
                        "resultaat": resultaat
                    })
                    
                except ValueError as e:
                    error_msg = str(e)
                    logging.error(f"Validatie fout: {error_msg}")
                    
                    # Log validatie fout naar BigQuery
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    log_to_bigquery(
                        route=request.path,
                        source=bron,
                        script_name=script,
                        status="fout",
                        message=error_msg,
                        processing_time_ms=processing_time_ms,
                        request_id=getattr(request, 'script_id', None),
                        payload=data if 'data' in locals() else None,
                        error_details={"type": "ValueError"},
                        retry_count=retry_count
                    )
                    
                    return jsonify({
                        "error": error_msg,
                        "script_id": getattr(request, 'script_id', None)
                    }), 400
                    
                except PermissionError as e:
                    error_msg = str(e)
                    logging.error(f"Authenticatie fout: {error_msg}")
                    
                    # Log authenticatie fout naar BigQuery
                    processing_time_ms = int((time.time() - start_time) * 1000)
                    log_to_bigquery(
                        route=request.path,
                        source=bron,
                        script_name=script,
                        status="fout",
                        message=error_msg,
                        processing_time_ms=processing_time_ms,
                        request_id=getattr(request, 'script_id', None),
                        payload=data if 'data' in locals() else None,
                        error_details={"type": "PermissionError"},
                        retry_count=retry_count
                    )
                    
                    return jsonify({
                        "error": error_msg,
                        "script_id": getattr(request, 'script_id', None)
                    }), 401
                    
                except Exception as e:
                    error_msg = str(e)
                    if retry_count == config.retry_config['max_retries']:
                        logging.error(f"Maximaal aantal pogingen ({config.retry_config['max_retries']}) bereikt voor route {request.path}")
                        
                        # Log max retries fout naar BigQuery
                        processing_time_ms = int((time.time() - start_time) * 1000)
                        log_to_bigquery(
                            route=request.path,
                            source=bron,
                            script_name=script,
                            status="fout",
                            message=f"Maximaal aantal pogingen ({config.retry_config['max_retries']}) bereikt",
                            processing_time_ms=processing_time_ms,
                            request_id=getattr(request, 'script_id', None),
                            payload=data if 'data' in locals() else None,
                            error_details={"type": type(e).__name__, "message": error_msg},
                            retry_count=retry_count
                        )
                        
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