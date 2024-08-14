def update_field_values(current_fields, updates):
    # Maak een dictionary van de huidige velden voor snelle toegang
    updated_fields_dict = {field['field']: field for field in current_fields}
    new_fields_dict = {}

    # Loop door de updates
    for update in updates:
        field_id = update['field']
        value_to_add = int(update['value'])

        if field_id in updated_fields_dict:
            # Update de waarde als het veld al bestaat
            updated_fields_dict[field_id]['value'] = int(updated_fields_dict[field_id]['value']) + value_to_add
        else:
            # Voeg het veld toe als het nog niet bestaat
            if field_id in new_fields_dict:
                new_fields_dict[field_id]['value'] = int(new_fields_dict[field_id]['value']) + value_to_add
            else:
                new_fields_dict[field_id] = {'field': field_id, 'value': value_to_add}

    # Zet de dictionary terug om een lijst te krijgen
    updated_fields = list(updated_fields_dict.values())
    new_fields = list(new_fields_dict.values())
    
    return updated_fields, new_fields

def add_or_update_last_ordered_item(updated_fields, new_fields, last_ordered_item):

    # Check updated_fields if there is a field with id 13, if so update the value of that field with last_ordered_item, if no field with id 13, add a new field with id 13 and value last_ordered_item to new_fields

    for field in updated_fields:
        if field['field'] == '13':
            field['value'] = last_ordered_item
            break
    else:
        new_fields.append({'field': '13', 'value': last_ordered_item})

    return updated_fields, new_fields