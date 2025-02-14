from flask import request
import logging
import hashlib
import base64
import hmac
import json

def validate_signature(request, secret):
    raw_payload = request.get_data()  # Dit moet de exacte bytes zijn
    received_signature = request.headers.get('X-WC-Webhook-Signature')

    computed_signature = base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_payload, hashlib.sha256).digest()
    ).decode("utf-8")

    logging.info(f"Raw Payload: {raw_payload}")
    logging.info(f"Computed Signature: {computed_signature}")
    logging.info(f"Received Signature: {received_signature}")

    return hmac.compare_digest(received_signature, computed_signature)


def parse_request_data():
    return request.get_data()