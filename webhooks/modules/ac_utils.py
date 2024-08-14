import requests

def get_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token):
    url = active_campaign_api_url + f"contacts/{contact_id}/fieldValues"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    response = requests.get(url, headers=headers)
    return response.json()

def get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token):
    url = active_campaign_api_url + "contacts/"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    params = {'email': email}
    response = requests.get(url, headers=headers, params=params)
    return response.json()
    
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
        print(f"An error occurred: {e}")
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
            if response.status_code == 201:
                print(f"Succesfully added tag {tag['tag']} to contact with id {tag['contact']}")
            else:
                print(f"Failed to add tag {tag['tag']} to contact with id {tag['contact']}: {response.content}")

def update_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token, updated_fields=None, new_fields=None):
    url = active_campaign_api_url + "fieldValues"
    headers = {
        "accept": "application/json",
        "Api-Token": active_campaign_api_token
    }

    # Update existing fields
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
            if response.status_code == 200:
                print(f"Succesfully updated field {update['field']} with value {update['value']}")
            else:
                print(f"Failed to update field {update['field']} with value {update['value']}: {response.content}")

    # Add new fields
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
            if response.status_code == 201:
                print(f"Succesfully added new field {new['field']} with value {new['value']}")
            else:
                print(f"Failed to add new field {new['field']} with value {new['value']}: {response.content}")


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