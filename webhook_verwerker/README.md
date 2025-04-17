# Webhook Verwerker

Webhook verwerker voor Active Campaign integratie met WooCommerce.

## Setup

1. Environment variables instellen:
```bash
export SECRET_KEY="jouw_secret_key"
export ACTIVE_CAMPAIGN_API_URL="https://jouw-account.api-us1.com/api/3/"
export ACTIVE_CAMPAIGN_API_TOKEN="jouw_token"
export GEBRUIKERSNAAM="db_gebruiker"
export DATABASE="db_naam"
export PASSWORD="db_wachtwoord"
export SERVER="db_server"
```

2. Flask app starten:
```bash
python app.py
```

## Routes

### 1. Product Velden Update
**Endpoint:** `/webhook/ac/product_fields`  
**Method:** POST  
**Beschrijving:** Update product velden in Active Campaign op basis van WooCommerce order data.

**Gebruikte datapunten:**
```json
{
    "billing": {
        "email": "verplicht - wordt gebruikt om contact te vinden"
    },
    "line_items": [
        {
            "product_id": "verplicht - wordt gebruikt om productvelden te bepalen",
            "quantity": "verplicht - wordt gebruikt voor berekening totale waarde",
            "meta_data": [
                {
                    "key": "optioneel - alleen '_bump_purchase' en '_fkcart_upsell' worden gecheckt"
                }
            ]
        }
    ]
}
```

### 2. Product Tags
**Endpoint:** `/webhook/ac/product_tags`  
**Method:** POST  
**Beschrijving:** Voeg product tags toe in Active Campaign op basis van WooCommerce order data.

**Gebruikte datapunten:**
```json
{
    "billing": {
        "email": "verplicht - wordt gebruikt om contact te vinden"
    },
    "line_items": [
        {
            "product_id": "verplicht - wordt gebruikt om categorieën te bepalen"
        }
    ]
}
```

### 3. Abonnement Velden
**Endpoint:** `/webhook/ac/abonnement/velden`  
**Method:** POST  
**Beschrijving:** Update abonnement velden in Active Campaign.

**Gebruikte datapunten:**
```json
{
    "billing": {
        "email": "verplicht - wordt gebruikt om contact te vinden"
    }
}
```

### 4. Abonnement Tags
**Endpoint:** `/webhook/ac/abonnement/tags`  
**Method:** POST  
**Beschrijving:** Voeg abonnement tags toe in Active Campaign.

**Gebruikte datapunten:**
```json
{
    "billing": {
        "email": "verplicht - wordt gebruikt om contact te vinden"
    }
}
```

## Test Payloads

### Voorbeeld payload voor alle routes:
```json
{
    "billing": {
        "first_name": "Max",
        "last_name": "Rood",
        "email": "mgsrood@gmail.com"
    },
    "line_items": [
        {
            "product_id": "8719326399386",  // K4 product
            "quantity": "1",
            "meta_data": [
                {
                    "key": "_bump_purchase",
                    "value": "1"
                }
            ]
        },
        {
            "product_id": "8719327215111",  // Starter product
            "quantity": "2",
            "meta_data": []
        }
    ]
}
```

## Postman Setup

1. **Basis Setup**:
   - Method: POST
   - URL: `http://localhost:5000/webhook/ac/[route]`
   - Headers:
     - Content-Type: application/json
     - X-WC-Webhook-Signature: [zie handtekening berekening]

2. **Handtekening berekenen**:
```python
import hmac
import hashlib
import json

payload = '{"billing":{"first_name":"Max",...}}'  # Je volledige JSON
secret = 'jouw_secret_key'  # Zelfde als in je .env file
signature = hmac.new(
    secret.encode('utf-8'),
    payload.encode('utf-8'),
    hashlib.sha256
).hexdigest()
print(signature)
```

## Product Mappings

### Product naar Veld Mapping:
```python
PRODUCT_TO_FIELD = {
    'W4': '9',  # Waterkefir
    'K4': '8',  # Kombucha
    'M4': '10', # Mix Originals
    'B12': '14',# Bloem
    'C12': '15',# Citroen
    'F12': '17',# Frisdrank Mix
    'P28': '18',# Probiotica
    'S': '19',  # Starter
    'G12': '20' # Gember
}
```

### Categorie naar Veld Mapping:
```python
CATEGORY_TO_FIELD = {
    'Discount': '11'
}
``` 