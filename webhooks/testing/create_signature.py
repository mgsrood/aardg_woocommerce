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
payload = """{
        "id": 107207,
        "parent_id": 0,
        "status": "on-hold",
        "currency": "EUR",
        "version": "9.6.0",
        "prices_include_tax": true,
        "date_created": "2025-02-14T11:36:05",
        "date_modified": "2025-02-14T11:36:08",
        "discount_total": "0.00",
        "discount_tax": "0.00",
        "shipping_total": "3.99",
        "shipping_tax": "0.00",
        "cart_tax": "0.00",
        "total": "33.98",
        "total_tax": "0.00",
        "customer_id": 4252,
        "order_key": "wc_order_NiCEAxgPQQHSD",
        "billing": {
            "first_name": "Karlijne",
            "last_name": "Van damme",
            "company": "",
            "address_1": "Blasiusstraat 74-g",
            "address_2": "",
            "city": "Amsterdam",
            "state": "",
            "postcode": "1091 CW",
            "country": "NL",
            "email": "karlijnevandamme@gmail.com",
            "phone": ""
        },
        "shipping": {
            "first_name": "Karlijne",
            "last_name": "Van damme",
            "company": "",
            "address_1": "Blasiusstraat 74-g",
            "address_2": "",
            "city": "Amsterdam",
            "state": "",
            "postcode": "1091 CW",
            "country": "NL",
            "phone": ""
        },
        "payment_method": "mollie_wc_gateway_directdebit",
        "payment_method_title": "iDEAL",
        "customer_ip_address": "86.89.202.43",
        "customer_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36 Edg/99.0.1150.46",
        "created_via": "subscription",
        "customer_note": "",
        "cart_hash": "",
        "number": "107207"
    }"""

signature = generate_wc_signature(secret, payload)
print(signature)