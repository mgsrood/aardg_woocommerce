from flask import request
import logging
import hashlib
import base64
import hmac
import json

def validate_signature(request, secret):
    payload = request.get_data()
    signature = request.headers.get('X-WC-Webhook-Signature')
    computed_signature = base64.b64encode(
    bytes.fromhex(hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest())
).decode()
    
    # Logging voor debugging
    logging.info(f"Received signature: {signature}")
    logging.info(f"Received payload: {payload}")
    logging.info(f"Computed signature: {computed_signature}")
    
    return hmac.compare_digest(signature, computed_signature)

def parse_request_data():
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/json':
        return request.get_json(silent=True)
    elif content_type == 'application/x-www-form-urlencoded':
        form_data = request.form.to_dict(flat=False)
        for key in form_data:
            try:
                return json.loads(key)
            except json.JSONDecodeError:
                continue
    return None