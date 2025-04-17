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
  "id": 123,
  "parent_id": 0,
  "status": "active",
  "billing_period": "month",
  "billing_interval": 1,
  "start_date": "2025-04-01T00:00:00",
  "next_payment_date": "2025-05-01T00:00:00",
  "end_date": "2026-04-01T00:00:00",
  "payment_method": "stripe",
  "payment_method_title": "Credit Card",
  "customer_id": 456,
  "order_id": 789,
  "total": "30.00",
  "currency": "EUR",
  "subtotal": "25.00",
  "total_tax": "5.00",
  "subscription_key": "sub_abcdef123456",
  "user_id": 456,
  "billing": {
    "first_name": "John",
    "last_name": "Doe",
    "company": "",
    "address_1": "123 Main Street",
    "address_2": "Apt 101",
    "city": "Amsterdam",
    "state": "NH",
    "postcode": "1000AB",
    "country": "NL",
    "email": "john.doe@example.com",
    "phone": "+31 6 12345678"
  },
  "shipping": {
    "first_name": "John",
    "last_name": "Doe",
    "company": "",
    "address_1": "123 Main Street",
    "address_2": "Apt 101",
    "city": "Amsterdam",
    "state": "NH",
    "postcode": "1000AB",
    "country": "NL"
  },
  "line_items": [
    {
      "id": 1,
      "name": "Premium Subscription Plan",
      "product_id": 101,
      "variation_id": 0,
      "quantity": 1,
      "subtotal": "25.00",
      "total": "25.00",
      "tax": "5.00",
      "sku": "sub-premium",
      "price": "25.00"
    }
  ],
  "meta_data": [
    {
      "id": 1,
      "key": "_subscription_start_date",
      "value": "2025-04-01"
    },
    {
      "id": 2,
      "key": "_subscription_end_date",
      "value": "2026-04-01"
    }
  ],
  "date_created": "2025-04-01T00:00:00",
  "date_modified": "2025-04-02T12:00:00",
  "date_completed": null,
  "date_paid": "2025-04-01T00:00:00",
  "status_changes": [
    {
      "status": "active",
      "date": "2025-04-01T00:00:00"
    },
    {
      "status": "on-hold",
      "date": "2025-04-05T00:00:00"
    }
  ]
}"""

signature = generate_wc_signature(secret, payload)
print(signature)