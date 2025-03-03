# WooCommerce Klantenservice Applicatie

Een Flask applicatie voor het zoeken en bekijken van WooCommerce abonnementen.

## Functionaliteiten

- Zoeken op abonnements-ID
- Bekijken van abonnementsdetails
- Bekijken van alle abonnementen (alleen in SQLite modus)
- Ondersteuning voor zowel directe WooCommerce API als lokale SQLite database

## Installatie

1. Kloon deze repository
2. Maak een virtuele omgeving aan:
   ```
   python3 -m venv venv
   ```
3. Activeer de virtuele omgeving:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. Installeer de benodigde packages:
   ```
   pip install -r requirements.txt
   ```

## Configuratie

Maak een `.env` bestand aan in de hoofdmap van het project met de volgende inhoud:

```
# WooCommerce API Credentials
WOOCOMMERCE_URL=https://your-woocommerce-site.com/
WOOCOMMERCE_CONSUMER_KEY=your_consumer_key
WOOCOMMERCE_CONSUMER_SECRET=your_consumer_secret

# Database keuze
USE_SQLITE=true
SQLITE_DB_PATH=klantenservice_applicatie/data/woocommerce.db

# BigQuery Credentials (alleen nodig voor synchronisatie)
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
# Of gebruik GOOGLE_CREDENTIALS_JSON met de volledige JSON inhoud
# GOOGLE_CREDENTIALS_JSON={"type": "service_account", ...}

# BigQuery Project en Dataset
BIGQUERY_PROJECT_ID=your_project_id
BIGQUERY_DATASET=your_dataset
BIGQUERY_SUBSCRIPTIONS_TABLE=subscriptions
BIGQUERY_ORDERS_TABLE=orders
BIGQUERY_QUERY_LIMIT=1000
```

## Gebruik

### Directe WooCommerce API modus

Om de applicatie te gebruiken met directe verbinding naar de WooCommerce API:

1. Zet `USE_SQLITE=false` in het `.env` bestand
2. Zorg ervoor dat de WooCommerce API credentials correct zijn ingesteld
3. Start de applicatie:
   ```
   python app.py
   ```

### SQLite Database modus (aanbevolen)

Om de applicatie te gebruiken met een lokale SQLite database:

1. Zet `USE_SQLITE=true` in het `.env` bestand
2. Synchroniseer de data van BigQuery naar de lokale database:
   ```
   python sync_data.py
   ```
3. Start de applicatie:
   ```
   python app.py
   ```

### Data synchroniseren

Om de data van BigQuery naar de lokale SQLite database te synchroniseren:

```
python sync_data.py
```

Om de database te overschrijven als deze al bestaat:

```
python sync_data.py --force
```

## Toegang tot de applicatie

Open een webbrowser en ga naar:
```
http://127.0.0.1:5000
```

## Functionaliteiten

- **Zoeken op abonnements-ID**: Voer een abonnements-ID in om details te bekijken
- **Bekijken van abonnementsdetails**: Klik op de "Details" knop om alle informatie over een abonnement te zien
- **Bekijken van alle abonnementen**: Klik op "Bekijk alle abonnementen" om een lijst van alle abonnementen te zien (alleen beschikbaar in SQLite modus)

## Beperkingen

- Deze versie van de applicatie bevat geen ondersteuning voor abonnement items (subscription items) of verzendregels (shipping lines). Deze functionaliteit kan in een toekomstige versie worden toegevoegd. 