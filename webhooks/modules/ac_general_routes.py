from modules.ac_functions import update_active_campaign_product_fields, add_product_tag_ac
from modules.request import parse_request_data, validate_signature
from modules.config import set_script_id
from modules.log import log, end_log
from flask import jsonify
import request
import time

def ac_product_field_updater(greit_connection_string, klant, bron, wcapi, active_campaign_api_url, active_campaign_api_token, secret_key):
    # Route configuratie
    route_naam = "Updaten van product velden in Active Campaign"
    
    # Script ID bepalen
    start_time, script_id = set_script_id(greit_connection_string, klant, bron, "Script ID bepalen", route_naam)
    
    # Payload verwerken
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden", route_naam, script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    # Handtekening controleren
    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening", route_naam, script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)
    
    # Data verwerken
    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        
        # Functie uitvoeren
        if response.status_code == 200:
            order_data = response.json()
            update_active_campaign_product_fields(order_data, active_campaign_api_url, active_campaign_api_token, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Product velden bijgewerkt", route_naam, script_id, tabel=None)
            
            end_log(start_time, greit_connection_string, klant, bron, route_naam, script_id)
        
        else:
            log(greit_connection_string, klant, bron, f"FOUTMELDING: WCAPI response {response.status_code}", route_naam, script_id, tabel=None)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200

def ac_product_tag_adder(greit_connection_string, klant, bron, wcapi, active_campaign_api_url, active_campaign_api_token, secret_key):
        # Route configuratie
    route_naam = "Toevoegen van product tags in Active Campaign"
    
    # Script ID bepalen
    start_time, script_id = set_script_id(greit_connection_string, klant, bron, "Script ID bepalen", route_naam)
    
    # Payload verwerken
    data = parse_request_data()
    if not data:
        log(greit_connection_string, klant, bron, "FOUTMELDING: Geen payload gevonden", route_naam, script_id, tabel=None)
        return jsonify({'status': 'no payload'}), 200

    # Handtekening controleren
    if not validate_signature(request, secret_key):
        log(greit_connection_string, klant, bron, "FOUTMELDING: Ongeldige handtekening", route_naam, script_id, tabel=None)
        return "Invalid signature", 401
    
    # Voeg een vertraging van 20 seconden in
    time.sleep(20)
    
    # Data verwerken
    if 'id' in data:
        subscription_id = data['id']
        response = wcapi.get(f"subscriptions/{subscription_id}")
        
        # Functie uitvoeren
        if response.status_code == 200:
            order_data = response.json()
            add_product_tag_ac(order_data, active_campaign_api_url, active_campaign_api_token, greit_connection_string, klant, script_id)
            log(greit_connection_string, klant, bron, f"Product velden bijgewerkt", route_naam, script_id, tabel=None)
            
            end_log(start_time, greit_connection_string, klant, bron, route_naam, script_id)
        
        else:
            log(greit_connection_string, klant, bron, f"FOUTMELDING: WCAPI response {response.status_code}", route_naam, script_id, tabel=None)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200