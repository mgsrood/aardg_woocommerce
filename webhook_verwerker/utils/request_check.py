from flask import request
import hashlib
import base64
import hmac
import json

def validate_signature(request, secret):
    payload = request.get_data()
    signature = request.headers.get('X-WC-Webhook-Signature')
    computed_signature = base64.b64encode(hmac.new(secret.encode(), payload, hashlib.sha256).digest()).decode()
    
    return hmac.compare_digest(signature, computed_signature)

def parse_request_data():
    def nest_form_keys(flat_dict):
        nested = {}
        for key, value in flat_dict.items():
            if '[' in key and key.endswith(']'):
                outer, inner = key.split('[', 1)
                inner = inner[:-1]  # Remove trailing ']'
                nested.setdefault(outer, {})[inner] = value
            else:
                nested[key] = value
        return nested

    content_type = request.headers.get('Content-Type', '')

    if 'application/json' in content_type:
        data = request.get_json(silent=True)
    elif 'application/x-www-form-urlencoded' in content_type:
        flat_data = request.form.to_dict(flat=True)
        data = nest_form_keys(flat_data)
    else:
        data = None

    return data
    
    