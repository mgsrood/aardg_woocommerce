from facebook_business.adobjects.customaudience import CustomAudience
from facebook_business.api import FacebookAdsApi
from dotenv import load_dotenv
from modules.facebook_utils import renew_access_token
import os
import hashlib
from woocommerce import API
import json

# Load environment variables from .env file
load_dotenv()

# Get the GCP keys
app_id = os.getenv('FACEBOOK_APP_ID')
app_secret = os.getenv('FACEBOOK_APP_SECRET')
long_term_token = os.getenv('FACEBOOK_LONG_TERM_ACCESS_TOKEN')
ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')
custom_audience_id = os.getenv('FACEBOOK_CUSTOM_AUDIENCE_ID')
woocommerce_url = os.getenv('WOOCOMMERCE_URL')
consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')

# WCAPI
wcapi = API(
    url=woocommerce_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3",
    timeout=60
)

customer_id = '75'

# User GET Request
customer_data = wcapi.get(f'customers/{customer_id}').json()

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

try:
    FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=long_term_token)
except Exception as e:
    if 'Error validating access token' in str(e):
        print("Access token expired, renewing token...")
        new_token = renew_access_token()
        FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=long_term_token)
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

print(hashed_users)

# Bepaal het schema dat overeenkomt met de volgorde van de gegevens in hashed_users
schema = [
    "EMAIL", "PHONE", "FN", "LN", "CT", "ST", "ZIP", "COUNTRY"
]

# Voeg gebruikers toe aan de Custom Audience
response = custom_audience.add_users(
    schema=schema,
    users=hashed_users,
    is_raw=True  # Geeft aan dat de gegevens al gehasht zijn
)