from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi
from modules.facebook_utils import renew_access_token
import hashlib
from modules.log import log

def add_new_customers_to_facebook_audience(customer_data, app_id, app_secret, long_term_token, custom_audience_id, greit_connection_string, klant, script_id):
    # Account to add
    users = [
        {
            'email': f'{customer_data['email']}',
            'phone_number': f'{customer_data['billing']['phone']}',
            'first_name': f'{customer_data['billing']['first_name']}',
            'last_name': f'{customer_data['billing']['last_name']}',
            'city': f'{customer_data['billing']['city']}',
            'state': f'{customer_data['billing']['state']}',
            'country': f'{customer_data['billing']['country']}',
            'zip': f'{customer_data['billing']['postcode']}'
        }    ]

    # Initialiseer de Facebook Ads API
    log(greit_connection_string, klant, "WooCommerce | Facebook", "Facebook Ads API initialiseren", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
    try:
        FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=long_term_token)
    except Exception as e:
        log(greit_connection_string, klant, "WooCommerce | Facebook", f"FOUTMELDING: {e}", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        if 'Error validating access token' in str(e):
            print("Access token expired, renewing token...")
            log(greit_connection_string, klant, "WooCommerce | Facebook", "Access token verlopen, token vernieuwen", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
            try:
                new_token = renew_access_token()
                FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=new_token)
            except Exception as e:
                log(greit_connection_string, klant, "WooCommerce | Facebook", f"FOUTMELDING: {e}", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        else:
            raise

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
        log(greit_connection_string, klant, "WooCommerce | Facebook", "Gegevens normaliseren en hashen", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
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
        log(greit_connection_string, klant, "WooCommerce | Facebook", f"FOUTMELDING: {e}", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        raise

    # Bepaal het schema dat overeenkomt met de volgorde van de gegevens in hashed_users
    schema = [
        "EMAIL", "PHONE", "FN", "LN", "CT", "ST", "ZIP", "COUNTRY"
    ]

    # Voeg gebruikers toe aan de Custom Audience
    try:
        log(greit_connection_string, klant, "WooCommerce | Facebook", "Gebruikers toevoegen aan Facebook audience", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        response = custom_audience.add_users(
            schema=schema,
            users=hashed_users,
            is_raw=True  # Geeft aan dat de gegevens al gehasht zijn
        )
    except Exception as e:
        log(greit_connection_string, klant, "WooCommerce | Facebook", f"FOUTMELDING: {e}", "Nieuwe klanten toevoegen aan Facebook audience", script_id, tabel=None)
        raise