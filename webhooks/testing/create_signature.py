import hmac
import hashlib
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def generate_wc_signature(secret, payload):
    # Genereer de HMAC-SHA256 hash van de payload
    hmac_hash = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    # Codeer de hash naar Base64
    return base64.b64encode(hmac_hash).decode()

secret = os.getenv('SECRET_KEY')  
payload = '{"id": 103656}'

signature = generate_wc_signature(secret, payload)
print(signature)