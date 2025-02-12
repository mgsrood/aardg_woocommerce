from ac_modules.ac_utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, category_to_field_map, product_to_field_map, add_tag_to_contact
from g_modules.product_utils import get_discount_dict, get_category_one_dict, get_base_unit_values, get_sku_dict, get_key_from_product_id
from g_modules.utils import update_field_values, add_or_update_last_ordered_item
import logging

def update_active_campaign_product_fields(order_data, active_campaign_api_url, active_campaign_api_token):
    
    logging.info("Starten met bijwerken ActiveCampaign product velden")
    
    # Gewenste datapunten uit order data halen
    line_items = order_data['line_items']
    email = order_data.get('billing', {}).get('email')

    # De gewenste dictionaries ophalen
    try:
        sku_dict = get_sku_dict()
        discount_dict = get_discount_dict()
        base_unit_values_dict = get_base_unit_values()
    except Exception as e:
        logging.error(f"Fout bij het ophalen van de dictionaries: {e}")


    # Verwerken van de lineitems    
    logging.info(f"Ophalen order informatie voor: {email} / order_id {order_data['id']}")
    try:
        product_line_fields = [
            {"field": product_to_field_map[get_key_from_product_id(item['product_id'], sku_dict)], "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
            for item in line_items if get_key_from_product_id(item['product_id'], sku_dict) in product_to_field_map
        ]

        discount_line_fields = [
            {"field": '11', "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
            for item in line_items if get_key_from_product_id(item['product_id'], discount_dict) in category_to_field_map
        ]

        orderbump_line_fields = [
            {"field": '12', "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
            for item in line_items 
            if any(meta['key'] == '_bump_purchase' for meta in item.get('meta_data', []))
        ]

        fkcart_upsell_line_fields = [
            {"field": '22', "value": int(float(get_key_from_product_id(item['product_id'], base_unit_values_dict)) * float(item['quantity']))}
            for item in line_items 
            if any(meta['key'] == '_fkcart_upsell' for meta in item.get('meta_data', []))
        ]

        last_ordered_item = ["P_" + get_key_from_product_id(item['product_id'], sku_dict) for item in line_items]
        last_ordered_item = ','.join(last_ordered_item)
        
    except Exception as e:
        logging.error("Fout bij het verwerken van de lineitems: " + str(e))
        
    # Active Campaign data ophalen
    logging.info("Ophalen ActiveCampaign data voor: " + email)
    try:
        active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
        active_campaign_id = active_campaign_data['contacts'][0]['id']
        field_values = get_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token)['fieldValues']    
        current_fields = [
            {"field": item['field'], "value": item['value'], "id": item['id']}
            for item in field_values
        ]
        current_fields = sorted(current_fields, key=lambda x: int(x['field']))
    except Exception as e:
        logging.error("Fout bij het ophalen van ActiveCampaign data: " + str(e))

    # Update fields
    logging.info("Bijwerken ActiveCampaign product velden voor: " + email)
    try:
        updated_fields, new_fields = update_field_values(current_fields, product_line_fields + discount_line_fields + orderbump_line_fields + fkcart_upsell_line_fields)
        updated_fields, new_fields = add_or_update_last_ordered_item(updated_fields, new_fields, last_ordered_item)
        logging.info(f"Updated fields: {updated_fields}, New fields: {new_fields}")
    except Exception as e:
        logging.error("Fout bij het bijwerken van ActiveCampaign product velden: " + str(e))

    # Push updates to ActiveCampaign
    logging.info("Push updates naar ActiveCampaign voor: " + email)
    try:
        update_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token, updated_fields, new_fields)
    except Exception as e:
        logging.error("Fout bij het pushen van updates naar ActiveCampaign: " + str(e))


def add_product_tag_ac(order_data, active_campaign_api_url, active_campaign_api_token):
    
    logging.info("Starten met bijwerken ActiveCampaign tags")
    
    # Gewenste datapunten uit order data halen
    line_items = order_data['line_items']
    email = order_data.get('billing', {}).get('email')
    logging.info(f"Email: {email}")
    logging.info(f"Order_data: {order_data}")
    # ActiveCampaign ID ophalen
    logging.info("Ophalen ActiveCampaign ID voor: " + email)
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']

    # Gewenste tags
    logging.info("Ophalen gewenste tags en categoriën")
    desired_tags = {
        "Frisdrank": 112,
        "Starter": 114,
        "Bump": 111,
        "Originals": 102,
        "Challenge": 101,
        "Actie": 52,
        "a14_extra_starter": 136,
        "a14_extra_frisdrank": 137,
        "a3_extra_frisdrank": 138,
    }

    # Categoriën
    categories = get_category_one_dict()

    # Alle product categoriën
    category_list = []
    for item in line_items: 
        first_category = get_key_from_product_id(item['product_id'], categories)
        if first_category is not None:
            category_list.append(first_category)

    # Duplicaten verwijderen
    category_list = list(set(category_list))

    # Te verzenden tags
    if 'Challenge' in category_list:
        if 'Originals' in category_list:
            category_list.remove('Originals')
        if 'Starter' in category_list:
            category_list.remove('Starter')
            category_list.append('a14_extra_starter')
        if 'Frisdrank' in category_list:
            category_list.remove('Frisdrank')
            category_list.append('a14_extra_frisdrank')

    elif 'Originals' in category_list:
        if 'Starter' in category_list:
            category_list.remove('Starter')
            category_list.append('a14_extra_starter')
        if 'Frisdrank' in category_list:
            category_list.remove('Frisdrank')
            category_list.append('a14_extra_frisdrank')
            
    elif 'Starter' in category_list:
        if 'Frisdrank' in category_list:
            category_list.remove('Frisdrank')
            category_list.append('a3_extra_frisdrank')

    # Opnieuw tags verwijderen
    category_list = list(set(category_list))

    # Gewenste tags per categorie retourneren
    logging.info(f"Tags toevoegen aan contact voor {email}")
    for category in category_list:
        if category in desired_tags:
            abo_tag_id = desired_tags[category]
        tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]
        try:
            add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)
        except Exception as e:
            logging.error(f"{e}")
