from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import smtplib

# Sent email with attachments
def send_email_with_attachment(all_invoices, recipient_mail, order_details, smtp_server, smtp_port, sender_email, sender_password):
    # Configure the email
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
    for pdf_buffer, order_details in all_invoices:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())  # Haal de bytes uit het geheugen
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={order_details[0]}.pdf')
        message.attach(part)

    # Verbinding maken met de SMTP-server en e-mail verzenden
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

    print('E-mail met bijlage verzonden')