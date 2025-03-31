from ac_modules.ac_utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, add_tag_to_contact
import logging

def update_ac_abo_field(data, active_campaign_api_url, active_campaign_api_token):
    
    logging.info("Starten met bijwerken ActiveCampaign abonnement veld")
    
    # Gewenste datapunten uit data halen
    email = data.get('billing', {}).get('email')

    # Active Campaign data ophalen
    logging.info("Active Campaign contact ophalen voor: " + email)
    try:
        ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
        
        if not ac_data or not ac_data.get('contacts'):
            logging.error(f"Geen contact gevonden voor email: {email}")
            return

        # ActiveCampaign ID extraheren
        ac_id = ac_data['contacts'][0]['id']

        # Veld waarden ophalen
        field_values = get_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token)
        
        if not field_values:
            logging.error(f"Geen veldwaarden gevonden voor contact ID: {ac_id}")
            return

    except Exception as e:
        logging.error(f"Fout bij het ophalen van ActiveCampaign data: {e}")
        return  # Stop de functie als er een fout optreedt

    # Huidige waarden ophalen
    logging.info("Bepalen of abonnementstag is ingesteld voor: " + email)
    desired_field = 21
    contact_id = None
    current_abo_value = None
    specific_abo_field_id = None

    for item in field_values['fieldValues']:
        if int(item['field']) == desired_field:
            contact_id = item['contact']
            current_abo_value = item['value']
            specific_abo_field_id = item['id']
            break  # stop de loop zodra het gewenste veld is gevonden

    # Controleren of veld bestaat
    logging.info("Bijwerken van abonnement veld voor: " + email)
    if specific_abo_field_id:
        # Veld bestaat al, update het
        if current_abo_value and current_abo_value.isdigit():
            current_abo_value = int(current_abo_value)
        else:
            current_abo_value = 0  # Als het veld leeg is, begin met 0

        new_abo_value = current_abo_value + 1

        updated_field = {
            "id": specific_abo_field_id,
            "field": str(desired_field),
            "value": str(new_abo_value)
        }
        try:
            update_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token, updated_fields=[updated_field])
        except Exception as e:
            logging.error("Fout bij het bijwerken van ActiveCampaign abonnement veld: " + str(e))

    else:
        # Veld bestaat niet, voeg het toe
        new_field = {
            "contact": ac_id,
            "field": str(desired_field),
            "value": '1'
        }
        try:
            update_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token, new_fields=[new_field])
        except Exception as e:
            logging.error("Fout bij het bijwerken van ActiveCampaign abonnement veld: " + str(e))

def update_ac_abo_tag(woocommerce_data, active_campaign_api_url, active_campaign_api_token):
    
    logging.info("Starten met bijwerken ActiveCampaign abonnement tag")
    
    # Gewenste datapunten uit data halen
    email = woocommerce_data.get('billing', {}).get('email')

    # Active Campaign data ophalen
    logging.info("Active Campaign contact ophalen voor: " + email)
    try:
        active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
        
        if not active_campaign_data or not active_campaign_data.get('contacts'):
            logging.error(f"Geen contact gevonden voor email: {email}")
            return

        active_campaign_id = active_campaign_data['contacts'][0]['id']

        # Abonnemetns tag toevoegen
        abo_tag_id = 115
        tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]

        try:
            add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)
            logging.info("Abonnements tag toegevoegd voor: " + email)
        except Exception as e:
            logging.error("Fout bij het bijwerken van ActiveCampaign abonnement tag: " + str(e))
    except Exception as e:
        logging.error(f"Fout bij het ophalen van ActiveCampaign data: {e}")
        return