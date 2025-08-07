#!/usr/bin/env python3
"""
Test script voor lokale webhook testing van de WooCommerce Webhook Verwerker.

Dit script simuleert WooCommerce webhooks en test alle endpoints lokaal.
"""

import requests
import json
import time
import hashlib
import hmac
import base64
import os
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv

# Laad environment variabelen uit .env
load_dotenv()

# Test configuratie
BASE_URL = "http://localhost:8443" 
SECRET_KEY = os.getenv('SECRET_KEY', 'test_secret_key_123')

# Debug: Toon welke secret key wordt gebruikt
print(f"🔑 Gebruikt SECRET_KEY: {SECRET_KEY}")

class WebhookTester:
    def __init__(self, base_url=BASE_URL, secret_key=SECRET_KEY):
        self.base_url = base_url
        self.secret_key = secret_key
        self.session = requests.Session()
        
    def generate_signature(self, payload_data):
        """Genereer WooCommerce webhook signature - exact zoals in utils/request_check.py"""
        # De signature wordt berekend op de raw request data
        computed_signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode('utf-8'), 
                payload_data, 
                hashlib.sha256
            ).digest()
        ).decode()
        
        return computed_signature
    
    def send_webhook(self, endpoint, payload, needs_signature=True):
        """Verstuur een webhook naar het gegeven endpoint"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'WooCommerce/Test'
        }
        
        # Converteer payload naar JSON string voor signature en request body
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        if needs_signature:
            # Genereer signature op basis van de raw JSON string
            computed_signature = base64.b64encode(
                hmac.new(
                    self.secret_key.encode('utf-8'),
                    payload_json.encode('utf-8'),
                    hashlib.sha256
                ).digest()
            ).decode()
            headers['X-WC-Webhook-Signature'] = computed_signature
            
        try:
            print(f"\n🚀 Testing endpoint: {endpoint}")
            print(f"📦 Payload: {json.dumps(payload, indent=2)[:200]}...")
            
            # Verstuur de JSON string als data (niet als json parameter)
            response = self.session.post(url, data=payload_json, headers=headers, timeout=60)
            
            print(f"✅ Status: {response.status_code}")
            if response.text:
                print(f"📝 Response: {response.text[:200]}...")
                
            return response.status_code == 200
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Connectie fout - Is de server actief op {self.base_url}?")
            return False
        except requests.exceptions.Timeout:
            print("⏰ Timeout - Request duurde te lang")
            return False
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

def get_sample_payloads():
    """Sample webhook payloads voor verschillende scenario's"""
    
    # WooCommerce Order payload
    wc_order = {
        "id": 12345,
        "number": "12345",
        "order_key": "wc_order_abc123",
        "created_via": "checkout",
        "status": "completed",
        "currency": "EUR",
        "date_created": "2025-01-08T10:00:00",
        "date_modified": "2025-01-08T10:30:00",
        "discount_total": "0.00",
        "discount_tax": "0.00",
        "shipping_total": "5.00",
        "shipping_tax": "1.05",
        "cart_tax": "4.20",
        "total": "29.25",
        "total_tax": "5.25",
        "customer_id": 67890,
        "billing": {
            "first_name": "Jan",
            "last_name": "Jansen",
            "company": "",
            "address_1": "Teststraat 123",
            "address_2": "",
            "city": "Amsterdam",
            "state": "NH",
            "postcode": "1000 AA",
            "country": "NL",
            "email": "jan.jansen@test.nl",
            "phone": "0612345678"
        },
        "shipping": {
            "first_name": "Jan",
            "last_name": "Jansen",
            "company": "",
            "address_1": "Teststraat 123",
            "address_2": "",
            "city": "Amsterdam",
            "state": "NH",
            "postcode": "1000 AA",
            "country": "NL"
        },
        "payment_method": "ideal",
        "payment_method_title": "iDEAL",
        "transaction_id": "tr_abc123def456",
        "line_items": [
            {
                "id": 1,
                "name": "Aardg W4 Supplement",
                "product_id": 100,
                "variation_id": 0,
                "quantity": 2,
                "tax_class": "",
                "subtotal": "20.00",
                "subtotal_tax": "4.20",
                "total": "20.00",
                "total_tax": "4.20",
                "sku": "W4-SUP",
                "price": 10.00,
                "meta_data": [
                    {
                        "id": 123,
                        "key": "_subscription_period",
                        "value": "month"
                    }
                ]
            }
        ],
        "meta_data": [
            {
                "id": 456,
                "key": "_subscription_id",
                "value": "112330"
            }
        ]
    }
    
    # WooCommerce Subscription payload
    wc_subscription = {
        "id": 112330,
        "order_number": "112330",
        "status": "active",
        "currency": "EUR",
        "date_created": "2025-01-01T10:00:00",
        "date_modified": "2025-01-08T10:00:00",
        "total": "24.99",
        "customer_id": 67890,
        "billing_period": "month",
        "billing_interval": 1,
        "next_payment_date": "2025-08-31T19:38:38",
        "payment_method": "ideal",
        "payment_method_title": "iDEAL",
        "billing": {
            "first_name": "Jan",
            "last_name": "Jansen",
            "email": "jan.jansen@test.nl",
            "phone": "0612345678"
        },
        "line_items": [
            {
                "id": 1,
                "name": "Maandelijks Abonnement W4",
                "product_id": 100,
                "sku": "W4-MONTH",
                "quantity": 1,
                "total": "24.99"
            }
        ]
    }
    
    # Active Campaign Contact payload
    ac_contact = {
        "type": "contact",
        "date_time": "2025-01-08T10:00:00-06:00",
        "initiated_from": "admin",
        "initiated_by": "admin",
        "list": "1",
        "contact": {
            "id": "123456",
            "email": "jan.jansen@test.nl",
            "first_name": "Jan",
            "last_name": "Jansen",
            "fields": {
                "1": "Jan",
                "2": "Jansen",
                "3": "jan.jansen@test.nl"
            }
        }
    }
    
    # Facebook Audience payload (simpel)
    fb_audience = {
        "customer": {
            "email": "jan.jansen@test.nl",
            "first_name": "Jan",
            "last_name": "Jansen",
            "phone": "0612345678"
        },
        "event": "new_customer"
    }
    
    return {
        'wc_order': wc_order,
        'wc_subscription': wc_subscription,
        'ac_contact': ac_contact,
        'fb_audience': fb_audience
    }

def main():
    parser = argparse.ArgumentParser(description='Test WooCommerce Webhook Verwerker')
    parser.add_argument('--url', default=BASE_URL, help='Base URL van de server')
    parser.add_argument('--secret', default=SECRET_KEY, help='Secret key voor signature')
    parser.add_argument('--endpoint', help='Test alleen dit endpoint')
    parser.add_argument('--no-signature', action='store_true', help='Skip signature verificatie')
    parser.add_argument('--list', action='store_true', help='Toon alle beschikbare endpoints')
    
    args = parser.parse_args()
    
    # Test endpoints en hun configuraties
    test_endpoints = {
        '/woocommerce/update_ac_product_fields': {
            'payload_type': 'wc_order',
            'needs_signature': True,
            'description': 'Update Active Campaign product velden'
        },
        '/woocommerce/add_ac_product_tag': {
            'payload_type': 'wc_order',
            'needs_signature': True,
            'description': 'Voeg Active Campaign product tag toe'
        },
        '/woocommerce/increase_ac_abo_field': {
            'payload_type': 'wc_subscription',
            'needs_signature': True,
            'description': 'Verhoog Active Campaign abonnement veld'
        },
        '/woocommerce/decrease_ac_abo_field': {
            'payload_type': 'wc_subscription',
            'needs_signature': True,
            'description': 'Verlaag Active Campaign abonnement veld'
        },
        '/woocommerce/add_abo_tag': {
            'payload_type': 'wc_subscription',
            'needs_signature': True,
            'description': 'Voeg Active Campaign abonnement tag toe'
        },
        '/active_campaign/add_product': {
            'payload_type': 'ac_contact',
            'needs_signature': False,
            'description': 'Voeg Originals dummy product toe'
        },
        '/woocommerce/move_next_payment_date': {
            'payload_type': 'wc_subscription',
            'needs_signature': True,
            'description': 'Verplaats volgende betaaldatum'
        },
        '/woocommerce/update_or_add_subscription_to_bigquery': {
            'payload_type': 'wc_subscription',
            'needs_signature': True,
            'description': 'Synchroniseer abonnement naar BigQuery'
        },
        '/woocommerce/update_or_add_order_to_bigquery': {
            'payload_type': 'wc_order',
            'needs_signature': True,
            'description': 'Synchroniseer order naar BigQuery'
        },
        '/woocommerce/add_new_customers_to_facebook_audience': {
            'payload_type': 'fb_audience',
            'needs_signature': True,
            'description': 'Voeg klanten toe aan Facebook audience'
        }
    }
    
    if args.list:
        print("📋 Beschikbare endpoints:")
        for endpoint, config in test_endpoints.items():
            print(f"  {endpoint}")
            print(f"    📝 {config['description']}")
            print(f"    🔒 Signature: {'Ja' if config['needs_signature'] else 'Nee'}")
            print(f"    📦 Payload: {config['payload_type']}")
            print()
        return
    
    tester = WebhookTester(args.url, args.secret)
    payloads = get_sample_payloads()
    
    print("🧪 WooCommerce Webhook Verwerker Test Suite")
    print(f"🌐 Server: {args.url}")
    print(f"🔑 Secret: {'***' + args.secret[-3:] if len(args.secret) > 3 else '***'}")
    print("=" * 50)
    
    # Test specifiek endpoint of alle endpoints
    endpoints_to_test = [args.endpoint] if args.endpoint else test_endpoints.keys()
    
    success_count = 0
    total_count = 0
    
    for endpoint in endpoints_to_test:
        if endpoint not in test_endpoints:
            print(f"❌ Onbekend endpoint: {endpoint}")
            continue
            
        config = test_endpoints[endpoint]
        payload = payloads[config['payload_type']]
        needs_signature = config['needs_signature'] and not args.no_signature
        
        success = tester.send_webhook(endpoint, payload, needs_signature)
        if success:
            success_count += 1
        total_count += 1
        
        # Kleine pauze tussen requests
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print(f"📊 Resultaat: {success_count}/{total_count} endpoints geslaagd")
    
    if success_count == total_count:
        print("🎉 Alle tests geslaagd!")
    else:
        print("⚠️  Sommige tests zijn gefaald. Check de logs voor details.")

if __name__ == '__main__':
    main()