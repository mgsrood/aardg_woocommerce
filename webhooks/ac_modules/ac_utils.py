import requests
import logging
import json

def get_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token):
    url = active_campaign_api_url + f"contacts/{contact_id}/fieldValues"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    
    try:
        response = requests.get(url, headers=headers)
        return response.json()                          
    except Exception as e:
        logging.error(f"Fout bij het ophalen van ActiveCampaign velden: {e}")
        return None

def get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token):
    url = active_campaign_api_url + f"contacts?email={email}"
    logging.info(active_campaign_api_token)
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        logging.error(response.content)
        logging.error(f"Fout bij het ophalen van ActiveCampaign data: {e}")
        return None
    
def get_active_campaign_tag_data(active_campaign_api_url, active_campaign_api_token, search_key=None):
    url = f"{active_campaign_api_url}tags"
    if search_key:
        url += f"?search={search_key}"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}

    timeout = 10  # Stel de timeout in op 10 seconden
    
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Verhoogt een uitzondering bij een HTTP-foutstatus
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error("Fout bij het ophalen van ActiveCampaign tags: {}".format(e))
        return None

def add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token):
    url = active_campaign_api_url + "contactTags"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    for tag in tags:
            url = url
            payload = { "contactTag": {
            "contact": int(tag['contact']),
            "tag": int(tag['tag'])
        } }
            response = requests.post(url, json=payload, headers=headers)
            
            try:
                response_json = response.json()  # Probeer de JSON-response te parsen
            except json.JSONDecodeError:
                response_json = response.content  # Fallback als JSON-parsing mislukt

            logging.info(f"Status code: {response.status_code}")
            logging.info(f"Response content: {response_json}")
            
            if response.status_code in [200, 201]:  # Controleer meerdere succescodes
                logging.info(f"Tag {tag['tag']} succesvol toegevoegd aan contact {tag['contact']}")
            else:
                logging.error(f"Fout bij toevoegen tag {tag['tag']} aan contact {tag['contact']}: {response_json}")

def update_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token, updated_fields=None, new_fields=None):
    url = active_campaign_api_url + "fieldValues"
    headers = {
        "accept": "application/json",
        "Api-Token": active_campaign_api_token
    }

    # Bestaande velden updaten
    if updated_fields:
        for update in updated_fields:
            specific_field_url = url + f"/{update['id']}"
            payload = {
                "fieldValue": {
                    "contact": contact_id,
                    "field": update['field'],
                    "value": str(update['value'])
                },
                "useDefaults": False
            }
            response = requests.put(specific_field_url, json=payload, headers=headers)
            
            try:
                response_json = response.json()  # Probeer de JSON-response te parsen
            except json.JSONDecodeError:
                response_json = response.content  # Fallback als JSON-parsing mislukt

            logging.info(f"Status code: {response.status_code}")
            logging.info(f"Response content: {response_json}")
            
            if response.status_code in [200, 201]:  # Controleer meerdere succescodes
                logging.info(f"Veld {update['field']} geüpdatet met waarde {update['value']}")
            elif "No Result found for Field" in response.content.decode("utf-8"):
                logging.info(f"Geen resultaat gevonden voor veld {update['field']}. Geen update uitgevoerd.")
            else:
                logging.error(f"Veld {update['field']} mislukt geüpdatet met waarde {update['value']}: {response.content.decode('utf-8')}")

    # Nieuwe velden toevoegen
    if new_fields:
        for new in new_fields:
            payload = {
                "fieldValue": {
                    "contact": contact_id,
                    "field": new['field'],
                    "value": str(new['value'])
                },
                "useDefaults": False
            }
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code in [200, 201]:
                logging.info(f"Nieuw veld {new['field']} met waarde {new['value']} toegevoegd")
            else:
                logging.error(response.json())
                logging.error(f"Nieuw veld {new['field']} met waarde {new['value']} mislukt toe te voegen: {response.content}")


category_to_field_map = {
    'Discount': '11',
}

product_to_field_map = {
    'W4': '9', 
    'K4': '8', 
    'M4': '10', 
    'B12': '14', 
    'C12': '15', 
    'F12': '17', 
    'P28': '18', 
    'S': '19', 
    'G12': '20'
}