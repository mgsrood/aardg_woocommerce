import requests
import json
import logging

# Constants
TIMEOUT = 120
SUCCESS_CODES = [200, 201]

# Field mappings
CATEGORY_TO_FIELD = {
    'Discount': '11',
}

PRODUCT_TO_FIELD = {
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

def _make_request(method, url, headers, payload=None, timeout=TIMEOUT):
    """Helper functie voor HTTP requests."""
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        elif method == 'PUT':
            response = requests.put(url, json=payload, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Ongeldige HTTP methode: {method}")
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Request fout: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Ongeldige JSON response")

def update_field_values(current_fields, updates):
    """Update bestaande velden en voeg nieuwe toe."""
    updated_fields_dict = {field['field']: field for field in current_fields}
    new_fields_dict = {}
    changed_fields = 0

    for update in updates:
        field_id = update['field']
        value_to_add = int(update['value'])

        if field_id in updated_fields_dict:
            old_value = int(updated_fields_dict[field_id]['value'])
            new_value = old_value + value_to_add
            if new_value != old_value:  # Alleen tellen als de waarde is veranderd
                updated_fields_dict[field_id]['value'] = new_value
                changed_fields += 1
        else:
            if field_id in new_fields_dict:
                old_value = int(new_fields_dict[field_id]['value'])
                new_value = old_value + value_to_add
                if new_value != old_value:  # Alleen tellen als de waarde is veranderd
                    new_fields_dict[field_id]['value'] = new_value
                    changed_fields += 1
            else:
                new_fields_dict[field_id] = {'field': field_id, 'value': value_to_add}
                changed_fields += 1

    return list(updated_fields_dict.values()), list(new_fields_dict.values()), changed_fields

def add_or_update_last_ordered_item(updated_fields, new_fields, last_ordered_item):
    """Update of voeg last ordered item toe."""
    changed = False
    for field in updated_fields:
        if field['field'] == '13':
            if field['value'] != last_ordered_item:
                field['value'] = last_ordered_item
                changed = True
            break
    else:
        new_fields.append({'field': '13', 'value': last_ordered_item})
        changed = True

    return updated_fields, new_fields, changed

def get_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token):
    """Haal velden op voor een contact."""
    url = f"{active_campaign_api_url}contacts/{contact_id}/fieldValues"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    return _make_request('GET', url, headers)

def get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token):
    """Haal contact data op."""
    url = f"{active_campaign_api_url}contacts?email={email}"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    return _make_request('GET', url, headers)

def get_active_campaign_tag_data(active_campaign_api_url, active_campaign_api_token, search_key=None):
    """Haal tag data op."""
    url = f"{active_campaign_api_url}tags"
    if search_key:
        url += f"?search={search_key}"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    return _make_request('GET', url, headers)

def add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token):
    """Voeg tags toe aan een contact."""
    url = f"{active_campaign_api_url}contactTags"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}
    
    for tag in tags:
        payload = {
            "contactTag": {
                "contact": int(tag['contact']),
                "tag": int(tag['tag'])
            }
        }
        _make_request('POST', url, headers, payload)

def update_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token, updated_fields=None, new_fields=None):
    """Update bestaande velden en voeg nieuwe toe."""
    url = f"{active_campaign_api_url}fieldValues"
    headers = {"accept": "application/json", "Api-Token": active_campaign_api_token}

    # Update bestaande velden
    if updated_fields:
        for update in updated_fields:
            specific_url = f"{url}/{update['id']}"
            payload = {
                "fieldValue": {
                    "contact": contact_id,
                    "field": update['field'],
                    "value": str(update['value'])
                },
                "useDefaults": False
            }
            _make_request('PUT', specific_url, headers, payload)

    # Voeg nieuwe velden toe
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
            _make_request('POST', url, headers, payload)