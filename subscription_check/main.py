from woocommerce import API
from dotenv import load_dotenv
import os
import pandas as pd
from modules.utils import filter_subscriptions_with_price_difference, get_active_subscriptions, send_email_with_attachment, filter_subscriptions_with_price_mismatch

if __name__ == "__main__":
    load_dotenv()

    # Load environment variables
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')

    # Configuring the WooCommerce API
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )

    # SMTP configuratie
    smtp_server = os.getenv('MAIL_SMTP_SERVER')
    smtp_port = os.getenv('MAIL_SMTP_PORT')
    sender_email = os.getenv("MAIL_SENDER_EMAIL")
    smtp_username = sender_email
    smtp_password = os.getenv("MAIL_SENDER_PASSWORD")
    recipient_email = sender_email

    # Haal alle actieve abonnementen op
    subscriptions = get_active_subscriptions(wcapi)

    # Filter de abonnementen met afwijkende prijs
    filtered_subscriptions_price_diff = filter_subscriptions_with_price_difference(subscriptions)

    # Creëer een DataFrame voor abonnementen met afwijkende prijs
    df_price_diff = pd.DataFrame(filtered_subscriptions_price_diff)

    # Filter de abonnementen met een mismatch tussen line items en totaal prijs
    mismatch_subscriptions = filter_subscriptions_with_price_mismatch(subscriptions)

    # Creëer een DataFrame voor abonnementen met prijs mismatch
    df_mismatch = pd.DataFrame(mismatch_subscriptions)

    # Combineer beide DataFrames
    df_combined = pd.concat([df_price_diff, df_mismatch], ignore_index=True)

    # Exclude specific id's from DataFrame
    df = df_combined[~df_combined['Abonnement ID'].isin([4889, 7074, 34540])] # Maria Rood, Annemiek Bakker, Mirjam van der Meer

    # Optioneel: Exporteer naar een Excel-bestand
    file_path = "afwijkende_abonnementen.xlsx"
    df.to_excel(file_path, index=False)

    send_email_with_attachment(sender_email, recipient_email, smtp_server, smtp_port, smtp_username, smtp_password, file_path)

    # Verwijder het Excel-bestand na verzending
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Het bestand '{file_path}' is succesvol verwijderd.")
    else:
        print(f"Het bestand '{file_path}' kon niet worden gevonden.")

    print("E-mail succesvol verstuurd naar: " + recipient_email + ".")
