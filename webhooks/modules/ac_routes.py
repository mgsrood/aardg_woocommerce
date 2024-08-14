from modules.product_utils import get_discount_dict, get_category_one_dict, get_base_unit_values, get_sku_dict, get_key_from_product_id
from modules.product_utils import get_category_one_dict, get_sku_dict, get_discount_dict, get_base_unit_values, get_key_from_product_id
from modules.ac_utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, category_to_field_map, product_to_field_map, add_tag_to_contact
from modules.utils import update_field_values, add_or_update_last_ordered_item

# Actief
def update_active_campaign_product_fields(order_data, active_campaign_api_url, active_campaign_api_token, wcapi):
    line_items = order_data['line_items']
    email = order_data.get('billing', {}).get('email')

    # Get the appropriate dictionaries
    sku_dict = get_sku_dict(wcapi)
    discount_dict = get_discount_dict(wcapi)
    base_unit_values_dict = get_base_unit_values(wcapi)

    # Process lineitems to get product and category fields, plus last ordered items
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

    # Retrieve ActiveCampaign data
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']
    field_values = get_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token)['fieldValues']
    current_fields = [
        {"field": item['field'], "value": item['value'], "id": item['id']}
        for item in field_values
    ]
    current_fields = sorted(current_fields, key=lambda x: int(x['field']))

    # Update fields
    updated_fields, new_fields = update_field_values(current_fields, product_line_fields + discount_line_fields + orderbump_line_fields + fkcart_upsell_line_fields)
    updated_fields, new_fields = add_or_update_last_ordered_item(updated_fields, new_fields, last_ordered_item)

    # Push updates to ActiveCampaign
    update_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token, updated_fields, new_fields)

# Actief
def update_ac_abo_field(data, active_campaign_api_url, active_campaign_api_token):
    # Retrieve email
    email = data.get('billing', {}).get('email')

    # Retrieve ActiveCampaign contact
    ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)

    # Retrieve ActiveCampaign ID
    ac_id = ac_data['contacts'][0]['id']

    # Retrieve field values
    field_values = get_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token)

    # Extract current values
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
        update_active_campaign_fields(contact_id, active_campaign_api_url, active_campaign_api_token, updated_fields=[updated_field])

    else:
        # Veld bestaat niet, voeg het toe
        new_field = {
            "contact": ac_id,
            "field": str(desired_field),
            "value": '1'
        }
        update_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token, new_fields=[new_field])

# Actief
def update_ac_abo_tag(woocommerce_data, active_campaign_api_url, active_campaign_api_token):
    email = woocommerce_data.get('billing', {}).get('email')

    # Get ActiveCampaign ID
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']

    # Add Abo tag
    abo_tag_id = 115
    tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]

    add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)

# Actief
def add_product_tag_ac(woocommerce_data, active_campaign_api_url, active_campaign_api_token, wcapi):
    line_items = woocommerce_data['line_items']
    email = woocommerce_data.get('billing', {}).get('email')

    # Get ActiveCampaign ID
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']

    # Desired tags
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

    # Categories
    categories = get_category_one_dict(wcapi)

    # All product categories
    category_list = []
    for item in line_items: 
        first_category = get_key_from_product_id(item['product_id'], categories)
        if first_category is not None:
            category_list.append(first_category)

    # Remove duplicates
    category_list = list(set(category_list))

    # Tags to send
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

    # Again remove duplicates
    category_list = list(set(category_list))

    # Return desired tags for each category
    for category in category_list:
        if category in desired_tags:
            abo_tag_id = desired_tags[category]
        tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]
        add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)