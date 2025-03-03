# BigQuery Integratie voor Klantenservice Applicatie

Deze documentatie beschrijft hoe je de BigQuery integratie kunt gebruiken om margegegevens van orders op te halen en te tonen in de klantenservice applicatie.

## Vereisten

- Python 3.7 of hoger
- Google Cloud Platform account met toegang tot BigQuery
- Service account met leesrechten voor de BigQuery dataset

## Installatie

1. Installeer de benodigde packages:

```bash
pip install -r requirements-bigquery.txt
```

2. Configureer de omgevingsvariabelen:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="pad/naar/je/service-account-key.json"
```

Of voeg deze toe aan een `.env` bestand in de hoofdmap van de applicatie:

```
GOOGLE_APPLICATION_CREDENTIALS=pad/naar/je/service-account-key.json
```

## Gebruik

### Importeren van margegegevens

Om margegegevens uit BigQuery te importeren, voer je het volgende commando uit:

```bash
python import_bigquery_data.py
```

Dit commando haalt de gegevens op uit de `order_data.order_margin_data` tabel in BigQuery en slaat deze op in de SQLite database.

### Automatisch importeren bij opstarten

Je kunt het `start_app.sh` script gebruiken om de margegegevens automatisch te importeren bij het opstarten van de applicatie:

```bash
chmod +x start_app.sh
./start_app.sh
```

Zorg ervoor dat je het pad naar je service account key bestand aanpast in het script.

## Structuur van de margegegevens

De margegegevens worden opgeslagen in de `order_margin_data` tabel in de SQLite database met de volgende structuur:

- `order_id`: Het ID van de order
- `cost`: De kosten van de order
- `revenue`: De omzet van de order
- `margin`: De marge van de order (revenue - cost)
- `margin_percentage`: Het margepercentage van de order ((margin / revenue) * 100)
- `created_at`: De datum waarop de margegegevens zijn aangemaakt
- `updated_at`: De datum waarop de margegegevens voor het laatst zijn bijgewerkt

## Weergave in de applicatie

De margegegevens worden weergegeven op de orderdetailpagina, onder het kopje "Margegegevens". Hier zie je de kosten, omzet, marge en margepercentage van de order.

## Problemen oplossen

### Geen verbinding met BigQuery

Als je geen verbinding kunt maken met BigQuery, controleer dan of:

1. Het pad naar je service account key bestand correct is
2. Je service account de juiste rechten heeft voor de BigQuery dataset
3. De omgevingsvariabele `GOOGLE_APPLICATION_CREDENTIALS` correct is ingesteld

### Geen margegegevens zichtbaar

Als er geen margegegevens zichtbaar zijn op de orderdetailpagina, controleer dan of:

1. De order_id bestaat in de BigQuery tabel
2. De import succesvol is uitgevoerd
3. Er geen fouten zijn opgetreden tijdens de import

Je kunt de logbestanden controleren voor meer informatie over eventuele fouten. 