from f_modules.facebook_functions import add_new_customers_to_facebook_audience
from g_modules.request import parse_request_data, validate_signature
from g_modules.config import determine_script_id
from g_modules.log import end_log, setup_logging
from flask import jsonify, request
import logging
import time

def facebook_audience_customer_adder(greit_connection_string, klant, wcapi, secret_key, long_term_token, custom_audience_id, app_secret, app_id):
    
    # Configuratie
    start_time = time.time()
    script = "Facebook Audience"
    bron = "Facebook"
    
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
            customer_data = response.json()
            add_new_customers_to_facebook_audience(customer_data, app_id, app_secret, long_term_token, custom_audience_id)
            logging.info(f"Klant {customer_data['billing']['first_name'] + ' ' + customer_data['billing']['last_name']} verwerkt")
            
            # End logging
            end_log(start_time)
        
        else:
            logging.error("Klant kon niet worden toegevoegd aan Facebook audience: " + response.status_code)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200