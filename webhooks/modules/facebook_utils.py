from facebook_business.exceptions import FacebookRequestError
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.api import FacebookAdsApi
from dotenv import load_dotenv
import requests
import os

def update_env_file(new_token):
    with open('.env', 'r') as file:
        lines = file.readlines()

    with open('.env', 'w') as file:
        for line in lines:
            if line.startswith('FACEBOOK_LONG_TERM_ACCESS_TOKEN'):
                file.write(f"FACEBOOK_LONG_TERM_ACCESS_TOKEN={new_token}\n")
            else:
                file.write(line)

def initialize_facebook_api(app_id, app_secret, access_token):
    try:
        FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=access_token)
    except Exception as e:
        if 'Error validating access token' in str(e):
            print("Access token expired, renewing token...")
            new_token = renew_access_token(app_id, app_secret, access_token)
            if new_token:
                update_env_file(new_token)
                load_dotenv()  # Zorg ervoor dat de bijgewerkte waarde in je script wordt geladen
                FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=new_token)
                return new_token
        else:
            raise
    return access_token

def renew_access_token(app_id, app_secret, long_term_token):
    url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={long_term_token}"
    response = requests.get(url)
    if response.status_code == 200:
        new_token = response.json()['access_token']
        update_env_file(new_token)
        print(f"Access token renewed: {new_token}")
        return new_token
    else:
        raise Exception(f"Failed to renew access token: {response.text}")
    
def get_facebook_custom_audiences():
    # Load environment variables from .env file
    load_dotenv()

    # Get the GCP keys
    app_id = os.getenv('FACEBOOK_APP_ID')
    app_secret = os.getenv('FACEBOOK_APP_SECRET')
    long_term_token = os.getenv('FACEBOOK_LONG_TERM_ACCESS_TOKEN')
    ad_account_id = os.getenv('FACEBOOK_AD_ACCOUNT_ID')

    try:
        FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=long_term_token)
    except Exception as e:
        if 'Error validating access token' in str(e):
            print("Access token expired, renewing token...")
            new_token = renew_access_token(app_id, app_secret, long_term_token)
            FacebookAdsApi.init(app_id=app_id, app_secret=app_secret, access_token=new_token)
        else:
            raise

    # Maak een AdAccount object aan
    account = AdAccount(ad_account_id)

    # Specificeer de velden die je wilt ophalen
    fields = ['name', 'id']

    try:
        # Haal alle Custom Audiences op voor dit advertentieaccount
        audiences = account.get_custom_audiences(fields=fields)
        
        # Print de naam en ID van elke Custom Audience
        for audience in audiences:
            if 'name' in audience and 'id' in audience:
                print(f"Audience Name: {audience['name']}, Audience ID: {audience['id']}")
            else:
                print(f"Audience data incomplete: {audience}")
    except FacebookRequestError as e:
        print(f"Facebook API error: {e.api_error_message()}")
        print(f"Error type: {e.api_error_type()}")
        print(f"Error code: {e.api_error_code()}")
        print(f"Trace ID: {e.api_error_trace()}")


if __name__ == '__main__':
    get_facebook_custom_audiences()