from w_modules.wc_functions import update_or_insert_order_to_bigquery
from g_modules.request import parse_request_data, validate_signature
from g_modules.config import determine_script_id
from g_modules.log import end_log, setup_logging
from flask import jsonify, request
import logging
import time

def bigquery_order_processor(greit_connection_string, klant, wcapi, secret_key):
    
    # Configuratie
    start_time = time.time()
    script = "Order Verwerking"
    bron = "WooCommerce"
    
    # Script ID bepalen
    script_id = determine_script_id(greit_connection_string)
    
    # Set up logging (met database logging)
    setup_logging(greit_connection_string, klant, bron, script, script_id)
    
    # Payload verwerken
    data = parse_request_data()
    if not data:
        logging.warning("Geen payload gevonden")
        return jsonify({'status': 'no payload'}), 200

    # Handtekening controleren
    if not validate_signature(request, secret_key):
        logging.error("Ongeldige handtekening")
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)
    
    # Data verwerken
    if 'id' in data:
        order_id = data['id']
        response = wcapi.get(f"orders/{order_id}")
        
        # Functie uitvoeren
        if response.status_code == 200:
            
            # Customer data verwerken
            order_data = response.json()
            update_or_insert_order_to_bigquery(order_id, wcapi)
            logging.info(f"Order toegevoegd / geupdate voor {order_data['billing']['first_name'] + ' ' + order_data['billing']['last_name']}")
            
            # End logging
            end_log(start_time)
        
        else:
            logging.error(response.status_code)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200
