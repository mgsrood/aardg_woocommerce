from modules.wc_functions import update_or_insert_order_to_bigquery
from modules.request import parse_request_data, validate_signature
from modules.config import set_script_id
from modules.log import log, end_log
from flask import jsonify, request
import time

def bigquery_order_processor(greit_connection_string, klant, bron, wcapi, secret_key):
    
    # Route configuratie
    route_naam = "Order toevoegen of updaten in BigQuery"
    
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
        order_id = data['id']
        response = wcapi.get(f"orders/{order_id}")
        
        # Functie uitvoeren
        if response.status_code == 200:
            update_or_insert_order_to_bigquery(greit_connection_string, klant, script_id, route_naam, order_id, wcapi)
            log(greit_connection_string, klant, bron, f"Order {order_id} verwerkt", route_naam, script_id, tabel=None)
            
            end_log(start_time, greit_connection_string, klant, bron, route_naam, script_id)
        
        else:
            log(greit_connection_string, klant, bron, f"FOUTMELDING: WCAPI response {response.status_code}", route_naam, script_id, tabel=None)
            jsonify({'status': 'error'}), response.status_code

    return jsonify({'status': 'success'}), 200

