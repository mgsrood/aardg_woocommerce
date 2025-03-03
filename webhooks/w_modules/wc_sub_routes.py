from w_modules.wc_functions import move_next_payment_date, update_or_insert_sub_to_bigquery
from g_modules.request import parse_request_data, validate_signature
from g_modules.config import determine_script_id
from g_modules.log import end_log, setup_logging
from flask import jsonify, request
import traceback
import logging
import time

def subscription_payment_date_mover(greit_connection_string, klant, secret_key, wcapi):
    
    # Configuratie
    start_time = time.time()
    script = "Besteldatum"
    bron = "WooCommerce"
    
    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)
    
    # Set up logging (met database logging)
    db_handler = setup_logging(greit_connection_string, klant, bron, script, script_id)
    
    # Payload verwerken
    data = parse_request_data()
    if not data:
        logging.error("Geen payload gevonden")
        return jsonify({'status': 'no payload'}), 200

    # Handtekening controleren
    if not validate_signature(request, secret_key):
        logging.error("Ongeldige handtekening")
        return "Invalid signature", 401

    # Functie uitvoeren
    try:
        # Customer data verwerken
        move_next_payment_date(data, wcapi)
        logging.info(f"Abonnement toegevoegd / geupdate voor {data['billing']['first_name'] + ' ' + data['billing']['last_name']}")
        
        # Eindtijd logging
        end_log(start_time)
        
        # Logging afhandelen
        db_handler.flush_logs()
        logging.shutdown()
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logging.error(f"Fout opgetreden: {e}\n{traceback.format_exc()}")
        db_handler.flush_logs()
        logging.shutdown()
        
        return jsonify({'status': 'error'}), 500

    

def bigquery_subscription_processor(greit_connection_string, klant, secret_key):
    
    # Configuratie
    start_time = time.time()
    script = "Abonnement Verwerking"
    bron = "WooCommerce"
    
    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)
    
    # Set up logging (met database logging)
    db_handler = setup_logging(greit_connection_string, klant, bron, script, script_id)
    
    # Payload verwerken
    data = parse_request_data()
    if not data:
        logging.error("Geen payload gevonden")
        return jsonify({'status': 'no payload'}), 200

    # Handtekening controleren
    if not validate_signature(request, secret_key):
        logging.error("Ongeldige handtekening")
        return "Invalid signature", 401
    
    # Functie uitvoeren
    try:
        update_or_insert_sub_to_bigquery(data, data['id'])
        logging.info(f"Product velden bijgewerkt voor {data['billing']['first_name'] + ' ' + data['billing']['last_name']}")
        
        # Eindtijd logging
        end_log(start_time)
        
        # Logging afhandelen
        db_handler.flush_logs()
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logging.error(f"Fout opgetreden: {e}\n{traceback.format_exc()}")
        db_handler.flush_logs()
        
        return jsonify({'status': 'error'}), 500

    