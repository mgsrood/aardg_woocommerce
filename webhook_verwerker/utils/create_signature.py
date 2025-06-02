import hashlib
import base64
import hmac
import os

def generate_wc_signature(secret, payload):
    # Genereer de HMAC-SHA256 hash van de payload
    hmac_hash = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    # Codeer de hash naar Base64
    return base64.b64encode(hmac_hash).decode()

secret = "1234"
payload = """{
    "id": 54321,
    "status": "processing",
    "currency": "EUR",
    "total": "49.99",
    "billing": {
        "company": "Voorbeeld Corp",
        "city": "Utrecht",
        "state": "UT",
        "postcode": "3511 AA",
        "country": "NL",
        "email": "besteller@example.com",
        "first_name": "Petra",
        "last_name": "de Vries",
        "address_1": "Pleinweg 50",
        "address_2": "Appartement 3B"
    },
    "shipping": {
        "company": "",
        "city": "Utrecht",
        "state": "UT",
        "postcode": "3511 AA",
        "country": "NL",
        "first_name": "Petra",
        "last_name": "de Vries",
        "address_1": "Pleinweg 50",
        "address_2": "Appartement 3B"
    },
    "order_number": "ORD-54321-XYZ",
    "date_created": "2024-06-20T14:30:00",
    "date_modified": "2024-06-20T14:35:00",
    "discount_total": "10.00",
    "customer_id": 77,
    "order_key": "wc_order_abc123xyz",
    "payment_method": "bacs",
    "payment_method_title": "Direct Bank Transfer",
    "transaction_id": "",
    "customer_ip_address": "213.213.213.213",
    "customer_user_agent": "Chrome/90.0...",
    "created_via": "website",
    "customer_note": "",
    "date_completed": null,
    "date_paid": null,
    "cart_hash": "ch_jkl456",
    "line_items": [
        {
            "id": 301,
            "name": "Premium Widget",
            "product_id": 1001,
            "quantity": 1,
            "subtotal": "59.99",
            "total": "49.99",
            "price": 59.99
        }
    ],
    "coupon_lines": [
        {
            "id": 45,
            "code": "ZOMER10",
            "discount": "10.00"
        }
    ],
    "payment_url": "https://jousite.nl/checkout/order-pay/54321/?pay_for_order=true&key=wc_order_abc123xyz",
    "currency_symbol": "€",
    "shipping_total": "0.00"
}"""

signature = generate_wc_signature(secret, payload)
print(signature)