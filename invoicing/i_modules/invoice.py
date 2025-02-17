from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from fuzzywuzzy import fuzz
from io import BytesIO

# Function to transform hex to rgb
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    h_len = len(hex_color)
    return tuple(int(hex_color[i:i+h_len//3], 16)/255 for i in range(0, h_len, h_len//3))

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
def create_invoice_pdf(invoice_data, logo):
    
    # Colors
    blue = hex_to_rgb('19214E')
    red = hex_to_rgb('FF0046')
    pink = hex_to_rgb('FFE6EC')
    gray = hex_to_rgb('A3A6B8')
    
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter
    margin = 50

    # Add image
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
    pdf_buffer.seek(0)  # Ga terug naar het begin van het bestand
    return pdf_buffer