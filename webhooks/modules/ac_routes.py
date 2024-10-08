from modules.product_utils import get_discount_dict, get_category_one_dict, get_base_unit_values, get_sku_dict, get_key_from_product_id
from modules.ac_utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, category_to_field_map, product_to_field_map, add_tag_to_contact
from modules.utils import update_field_values, add_or_update_last_ordered_item
import logging

logger = logging.getLogger(__name__)

# Actief
def update_active_campaign_product_fields(order_data, active_campaign_api_url, active_campaign_api_token):
    logger.debug(f"Starting update_active_campaign_product_fields for: {order_data['billing']['email']}")
    line_items = order_data['line_items']
    email = order_data.get('billing', {}).get('email')

    # Get the appropriate dictionaries
    logger.debug(f"Getting the appropriate dictionaries")
    try:
        sku_dict = get_sku_dict()
        discount_dict = get_discount_dict()
        base_unit_values_dict = get_base_unit_values()
    except Exception as e:
        logger.error(f"Failed to get dictionaries: {e}")

    # Process lineitems to get product and category fields, plus last ordered items
    logger.debug(f"Retrieving order information for: {email} / order_id {order_data['id']}")
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
        logger.error(f"Failed to retrieve order data: {e}")

    # Retrieve ActiveCampaign data
    logger.debug(f"Retrieving ActiveCampaign data for: {email}")
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
        logger.error(f"Failed to retrieve ActiveCampaign data: {e}")

    # Update fields
    logger.debug(f"Updating fields for: {email}")
    try:
        updated_fields, new_fields = update_field_values(current_fields, product_line_fields + discount_line_fields + orderbump_line_fields + fkcart_upsell_line_fields)
        updated_fields, new_fields = add_or_update_last_ordered_item(updated_fields, new_fields, last_ordered_item)
    except Exception as e:
        logger.error(f"Failed to update fields: {e}")

    # Push updates to ActiveCampaign
    logger.debug(f"Pushing updates to ActiveCampaign for: {email}")
    try:
        update_active_campaign_fields(active_campaign_id, active_campaign_api_url, active_campaign_api_token, updated_fields, new_fields)
    except Exception as e:
        logger.error(f"Failed to push updates to ActiveCampaign: {e}")

# Actief
def update_ac_abo_field(data, active_campaign_api_url, active_campaign_api_token):
    logger.debug(f"Starting update_ac_abo_field for: {data['billing']['email']}")
    # Retrieve email
    email = data.get('billing', {}).get('email')

    # Retrieve ActiveCampaign contact
    logger.debug(f"Retrieving ActiveCampaign contact for: {email}")
    try:
        ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)

        # Retrieve ActiveCampaign ID
        ac_id = ac_data['contacts'][0]['id']

        # Retrieve field values
        field_values = get_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token)
    except Exception as e:
        logger.error(f"Failed to retrieve ActiveCampaign data: {e}")

    logger.debug(f"Determine is subscription tag is set: {email}")
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

    # Check if field exists
    logging.debug(f"Updated or apply new subscription field for: {email}")
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
            logger.error(f"Failed to update ActiveCampaign field: {e}")

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
            logger.error(f"Failed to add ActiveCampaign field: {e}")

# Actief
def update_ac_abo_tag(woocommerce_data, active_campaign_api_url, active_campaign_api_token):
    logging.debug(f"Starting update_ac_abo_tag for: {woocommerce_data['billing']['email']}")
    email = woocommerce_data.get('billing', {}).get('email')

    # Get ActiveCampaign ID
    logging.debug(f"Retrieving ActiveCampaign contact for: {email}")
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']

    # Add Abo tag
    abo_tag_id = 115
    tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]

    logging.debug(f"Adding Abo tag to contact for: {email}")
    try:
        add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)
    except Exception as e:
        logger.error(f"Failed to add Abo tag to contact: {e}")

# Actief
def add_product_tag_ac(woocommerce_data, active_campaign_api_url, active_campaign_api_token):
    logging.debug(f"Starting add_product_tag_ac for: {woocommerce_data['billing']['email']}")
    line_items = woocommerce_data['line_items']
    email = woocommerce_data.get('billing', {}).get('email')

    # Get ActiveCampaign ID
    logging.debug(f"Retrieving ActiveCampaign contact for: {email}")
    active_campaign_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    active_campaign_id = active_campaign_data['contacts'][0]['id']

    logging.debug("Retrieving desired tags and categories")
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
    categories = get_category_one_dict()

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

    logging.debug(f"Adding tags to contact for: {email}")
    # Return desired tags for each category
    for category in category_list:
        if category in desired_tags:
            abo_tag_id = desired_tags[category]
        tags = [{"contact": active_campaign_id, "tag": abo_tag_id}]
        try:
            add_tag_to_contact(tags, active_campaign_api_url, active_campaign_api_token)
        except Exception as e:
            logger.error(f"Failed to add tag to contact: {e}")