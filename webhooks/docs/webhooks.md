# Webhook Documentatie

## Overzicht

Deze applicatie verwerkt verschillende webhooks van WooCommerce. Elke webhook heeft zijn eigen specifieke doel en verwerking.

## Webhook Endpoints

### 1. Betaaldatum Verplaatsing
**Endpoint:** `/woocommerce/move_next_payment_date`
**Methode:** POST

#### Beschrijving
Verplaatst de volgende betaaldatum voor abonnementen met iDEAL of Bancontact als betaalmethode.

#### Trigger
- Bij wijziging van een abonnement
- Bij creatie van een nieuw abonnement

#### Verwerking
- Controleert betaalmethode (iDEAL/Bancontact)
- Verplaatst betaaldatum 7 dagen naar voren
- Logt de wijziging

#### Voorbeeld Payload
```json
{
    "id": 123,
    "payment_method": "ideal",
    "next_payment_date_gmt": "2024-03-10T12:00:00",
    "billing": {
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

### 2. BigQuery Order Synchronisatie
**Endpoint:** `/woocommerce/update_or_add_order_to_bigquery`
**Methode:** POST

#### Beschrijving
Synchroniseert ordergegevens naar BigQuery voor analyse.

#### Trigger
- Bij nieuwe order
- Bij orderwijziging
- Bij orderstatus wijziging

#### Verwerking
- Controleert of order bestaat in BigQuery
- Voegt toe of werkt bij
- Logt de synchronisatie

### 3. BigQuery Abonnement Synchronisatie
**Endpoint:** `/woocommerce/update_or_add_subscription_to_bigquery`
**Methode:** POST

#### Beschrijving
Synchroniseert abonnementsgegevens naar BigQuery.

#### Trigger
- Bij nieuw abonnement
- Bij abonnementswijziging
- Bij statuswijziging

#### Verwerking
- Controleert bestaand abonnement
- Synchroniseert alle velden
- Logt de actie

### 4. Active Campaign Veld Update
**Endpoint:** `/woocommerce/update_ac_abo_field`
**Methode:** POST

#### Beschrijving
Werkt abonnementsvelden bij in Active Campaign.

#### Trigger
- Bij abonnementswijziging
- Bij statuswijziging

#### Verwerking
- Zoekt contact in Active Campaign
- Werkt velden bij
- Logt de update

### 5. Active Campaign Tag Toevoeging
**Endpoint:** `/woocommerce/add_abo_tag`
**Methode:** POST

#### Beschrijving
Voegt tags toe aan contacten in Active Campaign.

#### Trigger
- Bij specifieke abonnementsacties
- Bij statuswijzigingen

#### Verwerking
- Identificeert contact
- Voegt tag toe
- Logt de actie

### 6. Facebook Audience Update
**Endpoint:** `/woocommerce/add_new_customers_to_facebook_audience`
**Methode:** POST

#### Beschrijving
Voegt nieuwe klanten toe aan Facebook custom audience.

#### Trigger
- Bij nieuwe klant
- Bij specifieke orderacties

#### Verwerking
- Verzamelt klantgegevens
- Voegt toe aan audience
- Logt de toevoeging

## Webhook Beveiliging

### Signature Validatie
Elke webhook moet een geldige signature bevatten:
```python
X-WC-Webhook-Signature: sha256_hmac(payload, secret_key)
```

### Error Responses
- 401: Ongeldige signature
- 400: Ongeldige payload
- 500: Verwerkingsfout

## Monitoring

### Logging
Alle webhook verwerking wordt gelogd in de database met:
- Uniek Script ID
- Timestamp
- Resultaat
- Eventuele errors

### Performance
- Typische verwerkingstijd: < 2 seconden
- Rate limiting: Geen
- Concurrent verwerking: Ondersteund

## Troubleshooting

### Veel voorkomende problemen
1. Ongeldige signature
   - Controleer SECRET_KEY
   - Controleer payload formatting

2. Timeout
   - Controleer API limieten
   - Controleer netwerkconnectiviteit

3. Dubbele verwerking
   - Controleer webhook instellingen
   - Controleer logs op dubbele Script IDs 