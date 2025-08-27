# Webhook Verwerker

Een Flask-gebaseerde webhook verwerker voor het verwerken van webhooks van verschillende bronnen (WooCommerce, Active Campaign, Facebook).

## Functionaliteiten

- Gestandaardiseerde webhook verwerking voor verschillende bronnen
- Automatische retry logica met exponentiële backoff
- Geïntegreerde logging naar Azure SQL Database
- Signature validatie voor beveiligde webhooks
- Gestandaardiseerde error handling

## Configuratie

### Omgevingsvariabelen

De volgende omgevingsvariabelen moeten worden ingesteld:

```bash
# Database configuratie
SERVER=your_server
DATABASE=your_database
GEBRUIKERSNAAM=your_username
PASSWORD=your_password

# Active Campaign configuratie
AC_API_KEY=your_api_key
AC_BASE_URL=your_base_url

# WooCommerce configuratie
WC_CONSUMER_KEY=your_consumer_key
WC_CONSUMER_SECRET=your_consumer_secret
WC_STORE_URL=your_store_url

# Facebook configuratie
FACEBOOK_TOKENS_PATH=/path/to/tokens.json
FACEBOOK_CUSTOM_AUDIENCE_ID=your_audience_id
FACEBOOK_AD_ACCOUNT_ID=your_account_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_APP_ID=your_app_id

# Algemene configuratie
ENVIRONMENT=development  # of 'production'
```





### Azure SQL Database Setup

Voer het SQL script uit om de webhook logging tabel aan te maken:

```sql
-- Voer dit uit in je Azure SQL Database
-- Zie sql/create_webhook_logs.sql voor het volledige script
```

De `WebhookLogs` tabel bevat de volgende informatie:
- **Basis logging**: Route, bron, status, verwerkingstijd
- **Webhook data**: Email, order/subscription ID, product arrays
- **Error details**: Error type en details bij fouten
- **Performance**: Verwerkingstijd en retry count

## Gebruik

### Route Initialisatie

Routes worden geïnitialiseerd met de `initialize_route` decorator:

```python
from utils.route_initializer import initialize_route, RouteConfig

@app.route('/woocommerce/update_order', methods=['POST'])
@initialize_route(
    config=RouteConfig(
        verify_signature=True,
        parse_data=True,
        secret_key=os.getenv('WC_WEBHOOK_SECRET'),
        retry_config={
            'max_retries': 5,
            'initial_backoff': 5,
            'max_backoff': 300
        }
    ),
    bron="WooCommerce",
    script="Order Update",
    process_func=process_order_update
)
def update_order():
    pass
```

### Logging

De webhook verwerker logt automatisch:

1. Naar Azure SQL Database voor gedetailleerde webhook logging
2. Naar SQL Server voor gedetailleerde logging (legacy)
3. Naar stdout voor debugging

## Ontwikkeling

### Installatie

```bash
pip install -r requirements.txt
```

### Lokaal draaien

```bash
python app.py
```

### Productie

De applicatie draait als een service op de server. Gebruik het restart script om de service te herstarten:

```bash
./restart_app.sh
```

## Structuur

```
webhook_verwerker/
├── active_campaign/
│   └── functions.py
├── facebook/
│   └── functions.py
├── utils/
│   ├── config.py
│   ├── log.py
│   ├── request_check.py
│   └── route_initializer.py
├── woocommerce_/
│   └── functions.py
├── app.py
├── requirements.txt
└── restart_app.sh
```

## Monitoring

De webhook verwerking kan worden gemonitord via:

1. Azure SQL Database `WebhookLogs` tabel voor webhook specifieke logs
2. SQL Server logging tabel voor gedetailleerde logs (legacy)
3. Server logs voor real-time monitoring

## Beveiliging

- Webhook signatures worden gevalideerd waar nodig

- Retry logica voorkomt overbelasting bij fouten
- Environment-specifieke configuratie

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