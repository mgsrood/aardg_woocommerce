from f_modules.facebook_functions import add_new_customers_to_facebook_audience
from g_modules.request import parse_request_data, validate_signature
from g_modules.config import determine_script_id
from g_modules.log import end_log, setup_logging
from flask import jsonify, request
import traceback
import logging
import time

def facebook_audience_customer_adder(greit_connection_string, klant, secret_key, long_term_token, custom_audience_id, app_secret, app_id):
    
    # Configuratie
    start_time = time.time()
    script = "Facebook Audience"
    bron = "Facebook"
    
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
    
    # Data verwerken
    try:
        # Customer data verwerken
        add_new_customers_to_facebook_audience(data, app_id, app_secret, long_term_token, custom_audience_id)
        logging.info(f"Klant {data['billing']['first_name'] + ' ' + data['billing']['last_name']} verwerkt")
        
        # Eindtijd logging
        end_log(start_time)
        
        # Logging afhandelen
        db_handler.flush_logs()
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logging.error(f"Fout opgetreden: {e}\n{traceback.format_exc()}")
        db_handler.flush_logs()
        
        return jsonify({'status': 'error'}), 500

    