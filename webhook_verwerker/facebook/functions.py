from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi
from facebook_business.exceptions import FacebookRequestError
import logging
import hashlib
import os
import json

def add_new_customers_to_facebook_audience(
    data
):
    """
    Voegt nieuwe klanten toe aan een Facebook Custom Audience.
    
    Args:
        data: De webhook data met klant informatie
    Returns:
        Dict met status en resultaat van de operatie
    """
    
    # Facebook variabelen
    tokens_path = os.getenv('FACEBOOK_TOKENS_PATH')
    custom_audience_id = os.getenv('FACEBOOK_CUSTOM_AUDIENCE_ID')
    app_secret = os.getenv('FACEBOOK_APP_SECRET')
    app_id = os.getenv('FACEBOOK_APP_ID')
    
    # Valideer basis configuratie
    if not all([tokens_path, custom_audience_id, app_secret, app_id]):
        msg = "Facebook configuratie is incompleet. Controleer de environment variables."
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg
        }
    
    # Laad Facebook token uit tokens.json
    try:
        with open(tokens_path, 'r') as f:
            tokens = json.load(f)
            long_term_token = tokens.get('facebook_long_term_access_token')
            if not long_term_token:
                msg = "Geen Facebook token gevonden in tokens.json"
                logging.error(msg)
                return {
                    'status': 'fout',
                    'bericht': msg
                }
    except FileNotFoundError:
        msg = f"Tokens bestand niet gevonden op: {tokens_path}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg
        }
    except json.JSONDecodeError:
        msg = f"Ongeldig JSON formaat in tokens bestand: {tokens_path}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg
        }
    except Exception as e:
        msg = f"Fout bij het laden van Facebook token: {str(e)}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg
        }
    
    try:
        # Haal klant informatie uit de data
        billing_info = data.get("billing", {})
        email = billing_info.get("email")
        first_name = billing_info.get("first_name")
        last_name = billing_info.get("last_name")
        phone = billing_info.get("phone")
        city = billing_info.get("city")
        state = billing_info.get("state")
        country = billing_info.get("country")
        postcode = billing_info.get("postcode")
        
        if not email:
            msg = "Geen email adres gevonden in de data"
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg
            }

        # Account to add
        users = [{
            'email': email,
            'phone_number': phone,
            'first_name': first_name,
            'last_name': last_name,
            'city': city,
            'state': state,
            'country': country,
            'zip': postcode
        }]

        # Initialiseer de Facebook API
        try:
            FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=long_term_token)
            logging.info("Initialisatie Facebook API geslaagd")
        except Exception as e:
            msg = f"Initialisatie Facebook API mislukt: {e}"
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }

        # Definieer de Custom Audience
        custom_audience = CustomAudience(custom_audience_id)

        # Functie om gegevens te normaliseren en te hashen
        def normalize_and_hash(value):
            if value:
                value = value.strip().lower()
            else:
                value = ''
            return hashlib.sha256(value.encode('utf-8')).hexdigest()

        # Normaliseer en hash de gegevens
        hashed_users = []
        try:
            logging.info("Gegevens normaliseren en hashen")
            for user in users:
                hashed_user = []
                hashed_user.append(normalize_and_hash(user.get('email')))
                hashed_user.append(normalize_and_hash(user.get('phone_number')))
                hashed_user.append(normalize_and_hash(user.get('first_name')))
                hashed_user.append(normalize_and_hash(user.get('last_name')))
                hashed_user.append(normalize_and_hash(user.get('city')))
                hashed_user.append(normalize_and_hash(user.get('state')))
                hashed_user.append(normalize_and_hash(user.get('zip')))
                hashed_user.append(normalize_and_hash(user.get('country')))
                hashed_users.append(hashed_user)
        except Exception as e:
            msg = f"Gegevens normaliseren en hashen mislukt: {e}"
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }

        # Schema voor de gehashte data
        schema = ["EMAIL", "PHONE", "FN", "LN", "CT", "ST", "ZIP", "COUNTRY"]

        # Voeg gebruikers toe aan de Custom Audience
        try:
            logging.info("Gebruikers toevoegen aan Facebook audience")
            response = custom_audience.add_users(
                schema=schema,
                users=hashed_users,
                is_raw=True
            )
            msg = f"Klant {email} succesvol toegevoegd aan Facebook Custom Audience"
            logging.info(msg)
            return {
                'status': 'succes',
                'bericht': msg,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }
        except FacebookRequestError as e:
            try:
                error_data = e.api_error_message()
                if isinstance(error_data, dict):
                    error_type = error_data.get('error', {}).get('type', '')
                    error_code = error_data.get('error', {}).get('code', 0)
                    error_subcode = error_data.get('error', {}).get('error_subcode', 0)
                    
                    # Check voor token-gerelateerde fouten
                    if error_type == 'OAuthException' and error_code == 190:
                        if error_subcode == 460:
                            msg = "Facebook access token is verlopen of ongeldig. Token moet vernieuwd worden."
                        else:
                            msg = f"Facebook authenticatie fout (code {error_code}, subcode {error_subcode}): {error_data.get('error', {}).get('message', '')}"
                    else:
                        msg = f"Facebook API fout: {error_data.get('error', {}).get('message', str(e))}"
                else:
                    msg = f"Facebook API fout: {str(e)}"
            except Exception as parse_error:
                msg = f"Facebook API fout: {str(e)}"
            
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }
        except Exception as e:
            msg = f"Onverwachte fout bij toevoegen aan Facebook audience: {str(e)}"
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }

    except Exception as e:
        msg = f"Onverwachte fout bij toevoegen aan Facebook Custom Audience: {str(e)}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg
        } 