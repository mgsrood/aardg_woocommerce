# Aard'g WooCommerce Webhook Verwerker

Deze applicatie verwerkt webhooks van WooCommerce voor Aard'g en zorgt voor de juiste verwerking in verschillende systemen.

## 🚀 Features

- Verwerking van WooCommerce webhooks
- Integratie met Active Campaign
- Facebook Audience synchronisatie
- BigQuery data verwerking
- Automatische betaaldatum aanpassingen

## 📋 Vereisten

- Python 3.8+
- SQL Server database
- WooCommerce API toegang
- Active Campaign API toegang
- Facebook API toegang
- Google Cloud Platform toegang

## ⚙️ Installatie

1. Clone de repository:
```bash
git clone [repository-url]
```

2. Installeer de dependencies:
```bash
pip install -r requirements.txt
```

3. Configureer de omgevingsvariabelen:
```bash
cp .env.example .env
# Vul de juiste waarden in in het .env bestand
```

## 🔧 Configuratie

De applicatie maakt gebruik van de volgende omgevingsvariabelen:

- `WOOCOMMERCE_CONSUMER_SECRET`: WooCommerce API secret
- `WOOCOMMERCE_CONSUMER_KEY`: WooCommerce API key
- `WOOCOMMERCE_URL`: URL van de WooCommerce shop
- `SECRET_KEY`: Geheime sleutel voor webhook validatie
- `ACTIVE_CAMPAIGN_API_TOKEN`: Active Campaign API token
- `ACTIVE_CAMPAIGN_API_URL`: Active Campaign API URL
- `FACEBOOK_LONG_TERM_ACCESS_TOKEN`: Facebook lange termijn toegangstoken
- `FACEBOOK_CUSTOM_AUDIENCE_ID`: Facebook Custom Audience ID
- `FACEBOOK_AD_ACCOUNT_ID`: Facebook Ad Account ID
- `FACEBOOK_APP_SECRET`: Facebook App Secret
- `FACEBOOK_APP_ID`: Facebook App ID

## 🚦 Gebruik

Start de applicatie:
```bash
python app.py
```

De applicatie zal starten op poort 8443 en is klaar om webhooks te ontvangen.

## 📚 Documentatie

Uitgebreide documentatie is beschikbaar in de `docs` directory:

- [Technische Documentatie](docs/technical.md)
- [Webhook Documentatie](docs/webhooks.md)
- [Troubleshooting Guide](docs/troubleshooting.md)

## 🔍 Monitoring

De applicatie logt alle activiteiten in de SQL Server database in de Logboek tabel. Elk verzoek krijgt een uniek Script ID toegewezen voor tracking doeleinden.

## 🛠 Onderhoud

- Controleer regelmatig de logs in de database
- Monitor de webhook verwerkingstijden
- Houd de dependencies up-to-date
- Controleer regelmatig de API limieten

## 🤝 Support

Bij vragen of problemen:
1. Raadpleeg eerst de [Troubleshooting Guide](docs/troubleshooting.md)
2. Controleer de logs in de database
3. Neem contact op met de ontwikkelaars

## 📄 Licentie

Intern gebruik - Aard'g 