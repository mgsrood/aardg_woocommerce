from flask import request
import logging
import hashlib
import base64
import hmac
import json

def validate_signature(request, secret):
    payload = request.get_data()
    signature = request.headers.get('X-WC-Webhook-Signature')
    computed_signature = base64.b64encode(hmac.new(secret.encode(), payload, hashlib.sha256).digest()).decode()
    
    # Logging voor debugging
    logging.info(f"Received signature: {signature}")
    logging.info(f"Received payload: {payload}")
    logging.info(f"Computed signature: {computed_signature}")
    
    return hmac.compare_digest(signature, computed_signature)

def parse_request_data():
    content_type = request.headers.get('Content-Type')
    logging.info(f"Content-Type ontvangen: {content_type}")

    # Log de ruwe payload direct
    raw_payload = request.get_data()
    logging.debug(f"Ruwe payload (bytes): {raw_payload}")

    # Als JSON, probeer te decoderen zonder mutaties
    if content_type == 'application/json':
        try:
            json_payload = request.get_json(silent=True)  # Kan de JSON herformatteren
            logging.debug(f"JSON payload (zoals Flask parsed): {json_payload}")

            # Herformatteer naar exacte JSON string zoals WooCommerce zou verwachten
            formatted_payload = json.dumps(json_payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            logging.debug(f"Geformatteerde JSON (zonder spaties/newlines): {formatted_payload}")

            return formatted_payload  # Dit is wat we voor de signature check moeten gebruiken
        except Exception as e:
            logging.error(f"JSON parsing fout: {e}")
            return None

    # Verwerking van `application/x-www-form-urlencoded`
    elif content_type == 'application/x-www-form-urlencoded':
        form_data = request.form.to_dict(flat=False)
        for key in form_data:
            try:
                parsed_data = json.loads(key)
                logging.debug(f"Parsed form-encoded JSON: {parsed_data}")
                return json.dumps(parsed_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            except json.JSONDecodeError:
                continue

    logging.warning("Geen geldige payload gevonden")
    return None