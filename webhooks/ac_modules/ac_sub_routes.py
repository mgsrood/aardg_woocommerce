from ac_modules.ac_sub_functions import update_ac_abo_field, update_ac_abo_tag
from g_modules.request import parse_request_data, validate_signature
from g_modules.config import determine_script_id
from g_modules.log import end_log, setup_logging
from flask import jsonify, request
import logging
import time

def ac_abo_field_updater(greit_connection_string, klant, wcapi, secret_key, active_campaign_api_url, active_campaign_api_token):
    
    # Configuratie
    start_time = time.time()
    script = "Abonnements Veld"
    bron = "Active Campaign"
    
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
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        
        # Functie uitvoeren
        if response.status_code == 200:
            
            # Customer data verwerken
            subscription_data = response.json()
            update_ac_abo_field(subscription_data, active_campaign_api_url, active_campaign_api_token)
            logging.info(f"Product velden bijgewerkt voor {subscription_data['billing']['first_name'] + ' ' + subscription_data['billing']['last_name']}")
            
            # End logging
            end_log(start_time)
        
        else:
            logging.error(response.status_code)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200

def ac_abo_tag_adder(greit_connection_string, klant, wcapi, secret_key, active_campaign_api_url, active_campaign_api_token):
    
    # Configuratie
    start_time = time.time()
    script = "Abonnements Tag"
    bron = "Active Campaign"
    
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
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        
        # Functie uitvoeren
        if response.status_code == 200:
            
            # Customer data verwerken
            subscription_data = response.json()
            update_ac_abo_tag(subscription_data, active_campaign_api_url, active_campaign_api_token)
            logging.info(f"Product velden bijgewerkt voor {subscription_data['billing']['first_name'] + ' ' + subscription_data['billing']['last_name']}")
            
            # End logging
            end_log(start_time)
        
        else:
            logging.error(response.status_code)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200