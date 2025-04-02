from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi
import logging
import hashlib

def add_new_customers_to_facebook_audience(customer_data, my_app_id, my_app_secret, long_term_token, custom_audience_id):
    # Account to add
    users = [
        {
            'email': f"{customer_data['email']}",
            'phone_number': f"{customer_data['billing']['phone']}",
            'first_name': f"{customer_data['billing']['first_name']}",
            'last_name': f"{customer_data['billing']['last_name']}",
            'city': f"{customer_data['billing']['city']}",
            'state': f"{customer_data['billing']['state']}",
            'country': f"{customer_data['billing']['country']}",
            'zip': f"{customer_data['billing']['postcode']}"
        }
    ]

    # Initialiseer de Facebook API (en vernieuw token indien nodig)
    try:
        FacebookAdsApi.init(app_id=my_app_id, app_secret=my_app_secret, access_token=long_term_token)
        logging.info("Initialisatie Facebook API geslaagd")
    except Exception as e:
        logging.error(f"Initialisatie Facebook API mislukt: {e}")

    # Definieer de Custom Audience
    custom_audience = CustomAudience(custom_audience_id)

    # Functie om gegevens te normaliseren en te hashen, als de waarde aanwezig is
    def normalize_and_hash(value):
        if value:
            # Normaliseer de waarde
            value = value.strip().lower()
        else:
            value = ''  # Gebruik een lege string als waarde None is
        
        # Hash de waarde met SHA-256
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
        logging.error(f"Gegevens normaliseren en hashen mislukt: {e}")
        raise

    # Bepaal het schema dat overeenkomt met de volgorde van de gegevens in hashed_users
    schema = [
        "EMAIL", "PHONE", "FN", "LN", "CT", "ST", "ZIP", "COUNTRY"
    ]

    # Voeg gebruikers toe aan de Custom Audience
    try:
        logging.info("Gebruikers toevoegen aan Facebook audience")
        response = custom_audience.add_users(
            schema=schema,
            users=hashed_users,
            is_raw=True  # Geeft aan dat de gegevens al gehasht zijn
        )
        logging.info(f"Gebruikers toevoegen aan Facebook audience geslaagd: {response}")
    except Exception as e:
        logging.error(f"Gebruikers toevoegen aan Facebook audience mislukt: {e}")
        raise