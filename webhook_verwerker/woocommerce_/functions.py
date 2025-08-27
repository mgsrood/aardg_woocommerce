from datetime import datetime, timedelta
from woocommerce import API
import logging
import os

def move_next_payment_date(data):
    """Verplaatst de volgende betaaldatum als de betaalmethode iDEAL of Bancontact is."""
    payment_method = data.get('payment_method_title')
    subscription_id = data.get('id') # Haal vroeg op voor logging en return
    next_payment_date_str = data.get('next_payment_date_gmt')

    logging.info(f"Start verwerking verplaatsing betaaldatum voor abonnement: {subscription_id}, betaalmethode: {payment_method}")

    if payment_method not in ['iDEAL', 'Bancontact']:
        msg = f'Betaalmethode ({payment_method}) vereist geen aanpassing van de betaaldatum voor abonnement {subscription_id}.'
        logging.info(msg)
        return {
            'status': 'geen_actie_nodig',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method
        }

    if not next_payment_date_str:
        msg = f"Volgende betaaldatum (next_payment_date_gmt) niet gevonden in data voor abonnement {subscription_id}."
        logging.warning(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method,
            'details': 'next_payment_date_gmt ontbreekt'
        }

    logging.info(f"Originele volgende betaaldatum voor abonnement {subscription_id}: {next_payment_date_str}")

    try:
        consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
        consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
        woocommerce_url = os.getenv('WOOCOMMERCE_URL')

        if not all([consumer_secret, consumer_key, woocommerce_url]):
            msg = f"Ontbrekende WooCommerce API configuratie (URL, Key of Secret) voor abonnement {subscription_id}."
            logging.error(msg)
            # Deze ValueError wordt hieronder opgevangen
            raise ValueError(msg) 

        wcapi = API(
            url=woocommerce_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=60
        )

        next_payment_date = datetime.strptime(next_payment_date_str, '%Y-%m-%dT%H:%M:%S')
        new_next_payment_date = next_payment_date - timedelta(days=7)
        
        # Gebruik 'next_payment_date' als key en formatteer de datum als YYYY-MM-DD HH:MM:SS
        update_data = {"next_payment_date": new_next_payment_date.strftime('%Y-%m-%d %H:%M:%S')}
        
        if not subscription_id:
            # Deze check is enigszins redundant geworden door de vroege fetch, maar behouden voor robuustheid.
            msg = f"Abonnements ID niet gevonden in data voor het bijwerken van de betaaldatum."
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'abonnements_id': None, # Expliciet None omdat het hier faalt
                'betaalmethode': payment_method,
                'details': 'subscription_id ontbreekt bij update poging'
            }

        response = wcapi.put(f"subscriptions/{subscription_id}", update_data)
        
        if response.status_code != 200:
            error_body_text = ""
            try:
                json_response = response.json()
                if isinstance(json_response, dict) and 'message' in json_response:
                    # Gebruik het bericht van de API als dat er is
                    error_body_text = f"API Bericht: {json_response.get('message')}"
                    if 'data' in json_response and json_response.get('data') is not None:
                        error_body_text += f", API Data: {json_response.get('data')}" 
                else:
                    error_body_text = f"Volledige API response: {response.text}"
            except ValueError: # response.json() faalt als het geen JSON is
                error_body_text = f"Volledige API response (geen JSON): {response.text}"

            msg = f"Fout bij verplaatsen van de betaaldatum voor abonnement {subscription_id}: {response.status_code}"
            # Log de volledige foutdetails
            logging.error(f"{msg} - Details: {error_body_text}")
            return {
                'status': 'fout',
                'bericht': msg,
                'abonnements_id': subscription_id,
                'betaalmethode': payment_method,
                # Geef de gedetailleerde foutmelding ook terug in de response
                'details': f"HTTP status: {response.status_code}. {error_body_text}"
            }
        else:
            # Gebruik het correcte datumformaat in het succesbericht
            formatted_new_date = new_next_payment_date.strftime('%Y-%m-%d %H:%M:%S')
            msg = f"Betaaldatum voor abonnement {subscription_id} succesvol verplaatst met 7 dagen naar {formatted_new_date}"
            logging.info(msg)
            return {
                'status': 'succes',
                'bericht': msg,
                'abonnements_id': subscription_id,
                'originele_betaaldatum': next_payment_date_str,
                'nieuwe_betaaldatum': formatted_new_date,
                'betaalmethode': payment_method
            }

    except ValueError as ve:
        # Vangt o.a. de strptime error en de handmatig gegooide ValueError voor API config
        msg = f"Fout bij verwerken betaaldatum voor abonnement {subscription_id}: {str(ve)}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method,
            'details': str(ve)
        }
    except Exception as e:
        msg = f"Algemene fout bij het verplaatsen van de betaaldatum voor abonnement {subscription_id}: {str(e)}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method,
            'details': str(e)
        }





