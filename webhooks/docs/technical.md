# Technische Documentatie

## Architectuur

De applicatie is opgebouwd uit verschillende modules:

### Modules

1. **w_modules** (WooCommerce)
   - Verwerking van WooCommerce webhooks
   - Aanpassing van betaaldata
   - Synchronisatie met BigQuery

2. **ac_modules** (Active Campaign)
   - Bijwerken van abonnementsvelden
   - Toevoegen van tags
   - Bijwerken van productvelden

3. **f_modules** (Facebook)
   - Toevoegen van klanten aan custom audiences
   - Synchronisatie van klantdata

4. **g_modules** (Algemeen)
   - Database connecties
   - Logging
   - Configuratie
   - Request verwerking

## Database Schema

### Logboek Tabel
```sql
CREATE TABLE Logboek (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Script_ID INT,
    Klant VARCHAR(50),
    Bron VARCHAR(50),
    Script VARCHAR(50),
    Niveau VARCHAR(10),
    Bericht TEXT,
    Timestamp DATETIME DEFAULT GETDATE()
)
```

## API Endpoints

### WooCommerce Endpoints

1. `/woocommerce/move_next_payment_date` (POST)
   - Verplaatst de volgende betaaldatum voor iDEAL/Bancontact betalingen
   - Vereist webhook signature validatie

2. `/woocommerce/update_or_add_order_to_bigquery` (POST)
   - Synchroniseert orderdata naar BigQuery
   - Vereist webhook signature validatie

3. `/woocommerce/update_or_add_subscription_to_bigquery` (POST)
   - Synchroniseert abonnementsdata naar BigQuery
   - Vereist webhook signature validatie

### Active Campaign Endpoints

1. `/woocommerce/update_ac_abo_field` (POST)
   - Werkt abonnementsvelden bij in Active Campaign
   - Vereist webhook signature validatie

2. `/woocommerce/add_abo_tag` (POST)
   - Voegt tags toe aan abonnementen
   - Vereist webhook signature validatie

### Facebook Endpoints

1. `/woocommerce/add_new_customers_to_facebook_audience` (POST)
   - Voegt nieuwe klanten toe aan Facebook custom audience
   - Vereist webhook signature validatie

## Beveiliging

### Webhook Validatie
- Elke webhook wordt gevalideerd met een signature check
- De signature wordt gegenereerd met de `SECRET_KEY`
- Ongeldige signatures resulteren in een 401 response

### API Toegang
- Alle externe API's gebruiken tokens/keys voor authenticatie
- Tokens worden opgeslagen in environment variables
- Geen gevoelige data in de code

## Error Handling

### Logging
- Alle errors worden gelogd in de database
- Elk request krijgt een uniek Script ID
- Logging bevat timestamp, niveau en gedetailleerd bericht

### Retry Mechanisme
- Database connecties hebben een retry mechanisme
- Maximum van 3 pogingen met 5 seconden tussentijd

## Performance

### Thread Safety
- Script ID generatie is thread-safe
- Gebruikt een global counter met threading.Lock
- Counter wordt geïnitialiseerd met hoogste ID uit database

### Database Connecties
- Connection pooling via pyodbc
- Automatische reconnect bij timeout
- Prepared statements voor queries

## Deployment

### Vereisten
- Python 3.8+
- SQL Server met ODBC Driver 18
- Toegang tot alle externe API's
- Correcte environment variables

### Monitoring
- Alle activiteit wordt gelogd in de database
- Script IDs voor request tracking
- Error logging voor probleemoplossing 