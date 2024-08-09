from modules.utils import sku_dict, get_sku_from_product_id, category_dict, get_category_from_product_id, update_field_values
from modules.woocommerce_utils import get_woocommerce_order_data
from modules.ac_utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, category_to_field_map, product_to_field_map, add_tag_to_contact
from modules.utils import update_field_values   

def update_active_campaign_product_fields(order_id, active_campaign_api_url, active_campaign_api_token, wcapi):
    woocommerce_data = get_woocommerce_order_data(order_id, wcapi)
    line_items = woocommerce_data['line_items']
    email = woocommerce_data.get('billing', {}).get('email')

    # Process lineitems to get product and category fields, plus last ordered items
    product_line_fields = [
        {"field": product_to_field_map[get_sku_from_product_id(item['product_id'], sku_dict)], "value": item['quantity']}
        for item in line_items if get_sku_from_product_id(item['product_id'], sku_dict) in product_to_field_map
    ]

    category_line_fields = [
        {"field": category_to_field_map[get_category_from_product_id(item['product_id'], category_dict)], "value": item['quantity']}
        for item in line_items if get_category_from_product_id(item['product_id'], category_dict) in category_to_field_map
    ]

    last_ordered_item = ["P_" + get_sku_from_product_id(item['product_id'], sku_dict) for item in line_items]

    # Retrieve ActiveCampaign data
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']
    field_values = get_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token)['fieldValues']
    current_fields = [
        {"field": item['field'], "value": item['value'], "id": item['id']}
        for item in field_values if item['field'] not in ['22', '23', '24']
    ]
    current_fields = sorted(current_fields, key=lambda x: int(x['field']))

    # Update fields
    current_fields = update_field_values(current_fields, product_line_fields + category_line_fields)
    for current_field in current_fields:
        if current_field['field'] == '13':
            current_field['value'] = last_ordered_item

    print("updated current_fields: ", current_fields)

    # Push updates to ActiveCampaign
    update_active_campaign_fields(active_campaign_id, current_fields, active_campaign_api_url, active_campaign_api_token)

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

    # Turn abo value into integer
    current_abo_value = int(current_abo_value)

    # Update abo value
    new_abo_value = current_abo_value + 1

    # Update field values
    update_active_campaign_fields(contact_id, [{
        "id": specific_abo_field_id,
        "field": str(desired_field),
        "value": str(new_abo_value)
    }], active_campaign_api_url, active_campaign_api_token)

def update_ac_abo_tag(woocommerce_data, active_campaign_api_url, active_campaign_api_token):
    email = woocommerce_data.get('billing', {}).get('email')

    # Get ActiveCampaign ID
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']

    # Add Abo tag
    abo_tag_id = 115
    tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]

    add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)