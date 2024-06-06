from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.units import mm
import json
from woocommerce import API
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import smtplib
from datetime import datetime, timedelta
from io import BytesIO
import io
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Define a list of order IDs to process
order_ids_str = os.environ.get('ORDER_IDS', '95195, 94137, 92949, 91994')
order_ids_list = order_ids_str.split(',')
order_ids = [int(order_id) for order_id in order_ids_list if order_id.strip()]

# Email
recipient_mail = os.environ.get('MAIL', 'mgsrood@gmail.com')

# Define the Monta API variables
api_url = os.environ.get('MONTA_API_URL')
username = os.environ.get('MONTA_API_USERNAME')
password = os.environ.get('MONTA_API_PASSWORD')

# Define the WooCommerce API variables
url = os.environ.get('AARDG_WOOCOMMERCE_URL')
consumer_key = os.environ.get('AARDG_WOOCOMMERCE_CONSUMER_KEY')
consumer_secret = os.environ.get('AARDG_WOOCOMMERCE_CONSUMER_SECRET')

# Define the Woocommerce API
wcapi = API(
    url=url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    version="wc/v3"
)

# Function to transform hex to rgb
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    h_len = len(hex_color)
    return tuple(int(hex_color[i:i+h_len//3], 16)/255 for i in range(0, h_len, h_len//3))

# Colors
blue = hex_to_rgb('19214E')
red = hex_to_rgb('FF0046')
pink = hex_to_rgb('FFE6EC')
gray = hex_to_rgb('A3A6B8')

# Function to get batch data
def get_batch_data(order_id):

    endpoint = f"order/{order_id}/batches"
    url = api_url + endpoint
    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password))
        if response.status_code == 200:
            response_data_2 = response.json()
        else: 
            print(f"Fout bij het verwerken van order {order_id}: Statuscode {response.status_code}")
            response_data_2 = {}
    except Exception as e:
        print(f"Fout bij het verwerken van order {order_id}: {str(e)}")
        response_data_2 = {}

    # Extract batch data
    batches = response_data_2.get('m_Item3', [])
    batch_list = []

    for batch_data in batches:
        batch_info = batch_data.get('batch', {})
        title = batch_info.get('title', None)  # Als 'title' ontbreekt, zal title None zijn
        batch_list.append(title)

    # Create an SKU dictionairy
    batch_sku_dict = {}

    for batch_data in response_data_2.get('m_Item3', []):
        sku = batch_data.get('sku', None)
        batch_info = batch_data.get('batch', {})
        title = batch_info.get('title', None)

        if sku and title:
            endpoint = f"product/{sku}"
            url = api_url + endpoint
            try:
                response = requests.get(url, auth=HTTPBasicAuth(username, password))
                if response.status_code == 200:
                    product_data = response.json()
                    product_name = product_data.get('Description', None)
                    if product_name:
                        batch_sku_dict[product_name] = title
            except Exception as e:
                print(f"Fout bij het ophalen van productinformatie voor SKU {sku}: {str(e)}")

    # Maak een kopie van de dictionary
    batch_sku_dict_copy = batch_sku_dict.copy()

    # Itereer over de kopie en update de oorspronkelijke dictionary
    for key, value in batch_sku_dict_copy.items():
        batch_sku_dict[key] = value

    return batch_sku_dict

# Function to extract and print order details
def extract_order_details(order_id):
    order_data = wcapi.get(f"orders/{order_id}").json()
    order_id = order_data.get('id', '')
    date_created_iso = order_data.get('date_created', '')
    if date_created_iso:
        date_created_obj = datetime.fromisoformat(date_created_iso)
        date_created = date_created_obj.strftime('%d-%m-%Y')
    else:
        date_created = ''
    company = order_data.get('billing', {}).get('company', '').title()
    first_name = order_data.get('billing', {}).get('first_name', '')
    last_name = order_data.get('billing', {}).get('last_name', '')
    name = f"{first_name.title()} {last_name.title()}" 
    address = order_data.get('billing', {}).get('address_1', '').title()
    postal_code = order_data.get('billing', {}).get('postcode', '')
    city = order_data.get('billing', {}).get('city', '').title()
    country_code = order_data.get('billing', {}).get('country', '')
    if country_code == 'NL':
        country_name = 'Nederland'
    elif country_code == 'BE':
        country_name = 'België'
    else:
        country_name = country_code
    shipping_total = order_data.get('shipping_total', '')
    if country_code == 'NL':
        btw_percentage = 0.09
    elif country_code == 'BE':
        btw_percentage = 0.06
    else:
        btw_percentage = 0.0
    if country_code == 'NL':
        btw = '(9%)'
    elif country_code == 'BE':
        btw = '(6%)'
    else:
        btw = ''
    total_value = order_data.get('total', '')

    product_lines = []
    for i, item in enumerate(order_data.get('line_items', []), 1):
        product_name = item.get('name', '')
        quantity = item.get('quantity', 0)
        product_price = item.get('price', '')
        subtotal = item.get('subtotal', '')
        sku = item.get('sku', '')
        product_name = product_name.capitalize()
        line = f"{i}. Product Naam: {product_name}, Aantal: {quantity}, Productbedrag: {product_price}, Subtotaal Bedrag: {subtotal}, SKU: {sku}"
        product_lines.append(line)

    mail = order_data.get('billing', {}).get('email', '')

    return order_id, date_created, company, name, address, postal_code, city, country_name, shipping_total, btw_percentage, btw, total_value, product_lines, mail, first_name

# Transform order_details
def transform_order_details(order_details, batch_sku_dict):

    # Invoice data
    invoice_data = {
        "factuurnummer": order_details[0],
        "factuurdatum": order_details[1],
        "bedrijf": order_details[2],
        "naam": order_details[3],
        "adres": order_details[4],
        "postcode": order_details[5],
        "stad": order_details[6],
        "land": order_details[7],
        "btw_nummer": "",
        "subtotaal": [],
        "verzendkosten": order_details[8],
        "btw": [],
        "btw_percentage": order_details[10],
        "totaal": order_details[11],
        "items": []
    }

    # Gegevens uit order_details omzetten naar items in invoice_data
    order_items = order_details[12] 

    for i, item_data in enumerate(order_items, 1):
        # Hier kun je de gegevens uit item_data halen en aan het item in invoice_data toevoegen
        product_name = item_data.split(", ")[0].split(": ")[1]
        label = 'Bio'
        quantity = item_data.split(", ")[1].split(": ")[1]
        price = item_data.split(", ")[2].split(": ")[1]
        subtotal = item_data.split(", ")[3].split(": ")[1]

        # Zoek de batch op basis van de beste overeenkomende productnaam
        best_match = None
        best_match_ratio = 0

        for product, batch in batch_sku_dict.items():
            ratio = fuzz.partial_ratio(product_name.lower(), product.lower())
            if ratio > best_match_ratio:
                best_match = batch
                best_match_batch = batch
                best_match_ratio = ratio

        # Als er een overeenkomst is gevonden, gebruik dan de batch van de beste overeenkomst
        if best_match:
            batch = best_match
        else:
            # Als er geen overeenkomst is gevonden, kun je een standaardwaarde instellen of een foutmelding genereren
            print(f"Geen overeenkomst gevonden voor productnaam: {product_name}")

        # Maak een nieuw item voor invoice_data en voeg het toe aan de lijst van items
        item = {
            "omschrijving": product_name.title(),
            "label": label,
            "aantal": quantity,
            "batch": batch,
            "prijs": price,
            "totaal": subtotal
        }
        invoice_data["items"].append(item)

    # Add subtotals to get subtotal
    subtotaal = 0
    for item_data in order_items:
        subtotal_str = item_data.split(", ")[3].split(": ")[1]
        # Verwijder het Euro symbool en vervang komma's door punten, en converteer naar een float
        subtotal = float(subtotal_str.replace("€", "").replace(",", ".").strip())
        subtotaal += subtotal
    invoice_data["subtotaal"] = round(subtotaal, 2)

    # Create the BTW
    btw_percentage = order_details[9]  
    totaal_bedrag = float(order_details[11])
    btw_bedrag = (totaal_bedrag / (1 + btw_percentage)) * btw_percentage
    btw_bedrag = round(btw_bedrag, 2)  
    invoice_data["btw"] = btw_bedrag

    return invoice_data

# Function to create an invoice based on invoice data
def create_invoice_pdf(invoice_data, pdf_file):
    c = canvas.Canvas(pdf_file, pagesize=letter)
    width, height = letter
    margin = 50

    # Add image
    logo = os.getenv('IMAGE_PATH')
    c.drawImage(logo, 340, 650, 80*mm, 29*mm)

    # Red square
    c.setFillColorRGB(*red)
    c.rect(50, 700, 115, 50, fill=1, stroke=0)

    # White text
    c.setFillColorRGB(1, 1, 1)  
    c.setFont("Helvetica-Bold", 20)  
    c.drawString(60, 718, "FACTUUR")

    # Invoice date and number
    c.setFillColorRGB(*blue) 
    c.setFont("Helvetica-Bold", 14) 
    c.drawString(50, 675, 'Factuurnummer')
    c.drawString(170, 675, 'Factuurdatum')
    c.setFont("Helvetica", 12) 
    c.drawString(50, 655, f'{invoice_data["factuurnummer"]}')
    c.drawString(170, 655, f'{invoice_data["factuurdatum"]}')
    
    # Invoice details customer
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 615, 'Factuurgegevens')
    c.setFont("Helvetica", 12)
    c.drawString(50, 595, f'{invoice_data["bedrijf"]}') 
    c.drawString(50, 575, f'{invoice_data["naam"]}')
    c.drawString(50, 555, f'{invoice_data["adres"]}')
    c.drawString(50, 535, f'{invoice_data["postcode"]} {invoice_data["stad"]}')
    c.drawString(50, 515, f'{invoice_data["land"]}')
    c.drawString(50, 495, f'{invoice_data["btw_nummer"]}')

    # Invoice details Aard'g
    c.setFont("Helvetica-Bold", 14)
    c.drawString(350, 615, "Aard'g V.O.F.")
    c.setFont("Helvetica", 12)
    c.drawString(350, 595, "1871VC Schoorl")
    c.drawString(350, 575, "Nederland")
    c.drawString(350, 555, "Rek. nr. NL29 KNAB 0257 2803 40")
    c.drawString(350, 535, "BTW nr. NL858701765B01")
    c.drawString(350, 515, "KVK nr. 71403280")

    # Lineitems
    data_1 = [['Product', 'Batch', 'Label', 'Aantal', 'Prijs', 'Totaal']]
    for item in invoice_data["items"]:
        data_1.append([item["omschrijving"], item["batch"], item["label"], item["aantal"], item["prijs"], item["totaal"]])
    col_widths = [250, 50, 50, 50, 50, 50]
    t = Table(data_1, colWidths=col_widths)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), red),
                           ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                           ('FONT', (0,0), (-1,0), 'Helvetica-Bold', 14),
                           ('TEXTCOLOR', (0,1), (-1,-1), blue),
                           ('FONT', (0,1), (-1,-1), 'Helvetica', 12),
                           ]))
    t.wrapOn(c, width, height)
    t.drawOn(c, margin, 400)

    # Line above labels
    c.setStrokeColorRGB(*red)
    c.setLineWidth(3)
    c.line(50, 200, 300, 200)

    # Labels
    data_2 = [
        ["Bio", "Biologisch Gecertificeerd"],
        ["Bio-controle", "BIO-NL-01"],
    ]
    t = Table(data_2)
    t.setStyle(TableStyle([('TEXTCOLOR', (0,0), (0,-1), blue),
                           ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 14),
                           ('TEXTCOLOR', (-1,0), (-1,-1), blue),
                           ('FONT', (-1,0), (-1,-1), 'Helvetica', 12),
                           ]))
    t.wrapOn(c, width, height)
    t.drawOn(c, 50, 145)

    # Line above totals
    c.setStrokeColorRGB(*red)
    c.setLineWidth(3)
    c.line(400, 250, 550, 250)

    # Totals
    data_3 = [
        ["Subtotaal", invoice_data["subtotaal"]],
        ["Verzendkosten", invoice_data["verzendkosten"]],
        [f"BTW {invoice_data['btw_percentage']}", invoice_data["btw"]],
        ["Totaal", invoice_data["totaal"]]
    ]
    t = Table(data_3)
    t.setStyle(TableStyle([('TEXTCOLOR', (0,0), (0,-1), blue),
                           ('FONT', (0,0), (0,-1), 'Helvetica-Bold', 14),
                           ('TEXTCOLOR', (-1,0), (-1,-1), blue),
                           ('FONT', (-1,0), (-1,-1), 'Helvetica', 12),
                           ]))
    t.wrapOn(c, width, height)
    t.drawOn(c, 400, 145)

    # Line under totals
    c.setStrokeColorRGB(*red) 
    c.setLineWidth(3)
    c.line(50, 130, 550, 130)

    # Contactdetails Aard'g
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, 100, "E-mail:")
    c.setFont("Helvetica", 11)
    c.drawString(99, 100, "info@aardg.nl")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(184, 98, "•")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(209, 100, "Telefoonnummer:")
    c.setFont("Helvetica", 11)
    c.drawString(324, 100, "072-2029144")
    c.setFont("Helvetica-Bold", 20)
    c.drawString(400, 98, "•")
    c.setFont("Helvetica-Bold", 13)
    c.drawString(420, 100, "Website:")
    c.setFont("Helvetica", 11)
    c.drawString(480, 100, "www.aardg.nl")

    # Line under contactdetails Aard'g
    c.setStrokeColorRGB(*red) 
    c.setLineWidth(3)
    c.line(50, 80, 550, 80)

    c.save()

# Create an emptu list of invoices
all_invoices = []

# Function to process a single order
for order_id in order_ids:
    pdf_file = f"{order_id}.pdf"
    batch_sku_dict = get_batch_data(order_id)
    order_details = extract_order_details(order_id)
    invoice_data = transform_order_details(order_details, batch_sku_dict)
    create_invoice_pdf(invoice_data, pdf_file)
    all_invoices.append((pdf_file, order_details))

# Sent email with attachments
def send_email_with_attachment(all_invoices, recipient_mail, order_details):
    # Configure the email
    smtp_server = os.environ.get('MAIL_SMTP_SERVER')
    smtp_port = os.environ.get('MAIL_SMTP_PORT')
    sender_email = os.environ.get('MAIL_SENDER_EMAIL')
    sender_password = os.environ.get('MAIL_SENDER_PASSWORD')
    recipient_email = recipient_mail

    # Define the subject
    email_subject = f"""
    Facturen van Aard'g
    """

    # Bericht samenstellen
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = email_subject

    # Define the text
    email_text = f"""
    Hi {order_details[14]},

    Zie bijgevoegd de factuur of facturen van Aard'g.

    Als je nog meer facturen wilt ontvangen, stuur ons even een mailtje naar info@aardg.nl.

    Fijne dag!
    
    Groetjes,
    Max van Aard'g
    """

    message.attach(MIMEText(email_text, 'plain'))

    # Voeg de PDF als bijlage toe
    for pdf_file, order_details in all_invoices:
        pdf_attachment = open(pdf_file, 'rb')
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={order_details[0]}.pdf')
        message.attach(part)

    # Verbinding maken met de SMTP-server en e-mail verzenden
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

    print('E-mail met bijlage verzonden')

send_email_with_attachment(all_invoices, recipient_mail, order_details)