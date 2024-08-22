from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib
import json

def filter_subscriptions_with_price_difference(subscriptions, target_price=29.99):
    data = []

    for subscription in subscriptions:
        for item in subscription.get('line_items', []):
            if float(item['price']) != target_price:
                data.append({
                    'Abonnement ID': subscription['id'],
                    'Klant Naam': f"{subscription['billing']['first_name']} {subscription['billing']['last_name']}",
                    'Product': item['name'],
                    'Prijs': float(item['price'])
                })

    return data

def filter_subscriptions_with_price_mismatch(subscriptions):
    data = []

    for subscription in subscriptions:
        # Sum the line item prices
        total_price = sum(float(item['subtotal']) for item in subscription.get('line_items', []))

        # Add shipment
        total_price += float(subscription['shipping_total'])

        # Look up total price on the subscription
        if float(subscription['total']) != total_price:
            data.append({
                'Abonnement ID': subscription['id'],
                'Klant Naam': f"{subscription['billing']['first_name']} {subscription['billing']['last_name']}",
                'Product': 'Totaal',
                'Prijs': float(subscription['total'])
            })

    return data

def get_active_subscriptions(wcapi):
    subscriptions = []
    page = 1

    while True:
        response = wcapi.get(f"subscriptions?status=active&page={page}&per_page=100").json()
        if not response:
            break
        subscriptions.extend(response)
        print(f"Page {page}: {len(response)} abonnementen gevonden")
        page += 1

    return subscriptions

def send_email_with_attachment(sender_email, recipient_email, smtp_server, smtp_port, smtp_username, smtp_password, file_path):
    # Maak een MIMEMultipart object aan
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = 'Overzicht van Abonnementen met Afwijkende Prijs'

    # Voeg een tekstbericht toe
    body = "In de bijlage vind je het overzicht van abonnementen waarbij de prijs afwijkt van €29,99."
    msg.attach(MIMEText(body, 'plain'))

    # Voeg de Excel-bijlage toe
    with open(file_path, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {file_path}")
        msg.attach(part)

    # Verstuur de e-mail via SMTP
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(smtp_username, smtp_password)
    text = msg.as_string()
    server.sendmail(sender_email, recipient_email, text)
    server.quit()
