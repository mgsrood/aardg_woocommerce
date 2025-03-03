# Troubleshooting Guide

## Algemene Problemen

### 1. Webhook Verwerking Faalt

#### Symptomen
- 401 response
- Webhook wordt niet verwerkt
- Foutmelding in logs over ongeldige signature

#### Oplossing
1. Controleer de SECRET_KEY:
   ```bash
   echo $SECRET_KEY  # Moet overeenkomen met WooCommerce
   ```
2. Verifieer webhook instellingen in WooCommerce
3. Controleer logs op exacte foutmelding

### 2. Database Connectie Problemen

#### Symptomen
- "Kan geen verbinding maken met database" in logs
- Timeout errors
- Script IDs worden niet gegenereerd

#### Oplossing
1. Controleer database credentials:
   ```python
   # Controleer in .env:
   GEBRUIKERSNAAM=xxx
   DATABASE=xxx
   PASSWORD=xxx
   SERVER=xxx
   ```
2. Test netwerkconnectiviteit naar database
3. Controleer firewall instellingen

### 3. API Rate Limiting

#### Symptomen
- Timeout bij externe API calls
- "Too Many Requests" errors
- Vertraagde verwerking

#### Oplossing
1. Controleer API limieten:
   - WooCommerce: 25 requests/seconde
   - Active Campaign: 5 requests/seconde
   - Facebook: Varieert per endpoint
2. Implementeer rate limiting indien nodig
3. Spreid verwerking over tijd

### 4. Dubbele Script IDs

#### Symptomen
- Meerdere logs met hetzelfde Script ID
- Verwarring in logging
- Moeilijk te traceren problemen

#### Oplossing
1. Controleer thread-safety van counter
2. Herstart applicatie voor nieuwe counter
3. Controleer logs op timing issues

### 5. Memory Leaks

#### Symptomen
- Toenemend geheugengebruik
- Trage verwerking
- Server crashes

#### Oplossing
1. Monitor geheugengebruik:
   ```bash
   ps aux | grep python
   ```
2. Controleer op resource leaks
3. Herstart applicatie indien nodig

## Specifieke Problemen

### 1. Betaaldatum Verplaatsing Faalt

#### Symptomen
- "int object has no attribute 'put'" error
- Betaaldatum wordt niet aangepast
- WooCommerce API errors

#### Oplossing
1. Controleer WooCommerce API credentials
2. Verifieer webhook payload format
3. Controleer logging voor exacte foutpunt

### 2. BigQuery Synchronisatie Issues

#### Symptomen
- Data komt niet aan in BigQuery
- Duplicatie van records
- Schema mismatches

#### Oplossing
1. Controleer Google credentials
2. Verifieer BigQuery schema
3. Controleer data transformatie

### 3. Active Campaign Synchronisatie

#### Symptomen
- Tags worden niet toegevoegd
- Velden niet bijgewerkt
- Contact niet gevonden

#### Oplossing
1. Controleer Active Campaign API token
2. Verifieer contact matching
3. Controleer veld mappings

## Logging & Debugging

### Log Levels
```python
logging.ERROR    # Kritieke fouten
logging.WARNING  # Waarschuwingen
logging.INFO     # Informatieve berichten
logging.DEBUG    # Debug informatie
```

### Database Logging
```sql
-- Zoek specifieke fouten
SELECT * FROM Logboek 
WHERE Niveau = 'ERROR' 
ORDER BY Timestamp DESC;

-- Zoek specifiek Script ID
SELECT * FROM Logboek 
WHERE Script_ID = 12345 
ORDER BY Timestamp;
```

### Performance Monitoring
```sql
-- Gemiddelde verwerkingstijd
SELECT 
    Script_ID,
    DATEDIFF(second, MIN(Timestamp), MAX(Timestamp)) as ProcessingTime
FROM Logboek 
GROUP BY Script_ID;
```

## Preventie

### Dagelijkse Checks
1. Controleer error logs
2. Monitor API limieten
3. Verifieer database connectie
4. Check geheugengebruik

### Wekelijkse Maintenance
1. Cleanup oude logs
2. Controleer API tokens
3. Update dependencies indien nodig
4. Backup configuratie

## Contact

Bij aanhoudende problemen:
1. Verzamel relevante logs
2. Noteer exacte foutmeldingen
3. Documenteer reproductiestappen
4. Neem contact op met ontwikkelteam 