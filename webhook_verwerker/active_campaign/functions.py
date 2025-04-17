from active_campaign.utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, PRODUCT_TO_FIELD, CATEGORY_TO_FIELD, add_tag_to_contact
from utils.products import get_discount_dict, get_category_one_dict, get_base_unit_values, get_sku_dict, get_key_from_product_id
from active_campaign.utils import update_field_values, add_or_update_last_ordered_item
from woocommerce import API
import os

def _get_required_dicts():
    """Haalt alle benodigde dictionaries op in één keer."""
    return {
        'sku_dict': get_sku_dict(),
        'discount_dict': get_discount_dict(),
        'base_unit_values_dict': get_base_unit_values()
    }

def _process_line_items(line_items, dicts):
    """Verwerkt line items en genereert de benodigde velden."""
    product_line_fields = []
    discount_line_fields = []
    orderbump_line_fields = []
    fkcart_upsell_line_fields = []
    last_ordered_items = []

    for item in line_items:
        product_id = item['product_id']
        quantity = float(item['quantity'])
        base_value = float(get_key_from_product_id(product_id, dicts['base_unit_values_dict']))
        total_value = int(base_value * quantity)

        # Product velden
        if get_key_from_product_id(product_id, dicts['sku_dict']) in PRODUCT_TO_FIELD:
            product_line_fields.append({
                "field": PRODUCT_TO_FIELD[get_key_from_product_id(product_id, dicts['sku_dict'])],
                "value": total_value
            })

        # Discount velden
        if get_key_from_product_id(product_id, dicts['discount_dict']) in CATEGORY_TO_FIELD:
            discount_line_fields.append({
                "field": CATEGORY_TO_FIELD[get_key_from_product_id(product_id, dicts['discount_dict'])],
                "value": total_value
            })

        # Orderbump velden
        if any(meta['key'] == '_bump_purchase' for meta in item.get('meta_data', [])):
            orderbump_line_fields.append({
                "field": '12',
                "value": total_value
            })

        # FKCart upsell velden
        if any(meta['key'] == '_fkcart_upsell' for meta in item.get('meta_data', [])):
            fkcart_upsell_line_fields.append({
                "field": '22',
                "value": total_value
            })

        # Last ordered items
        last_ordered_items.append("P_" + get_key_from_product_id(product_id, dicts['sku_dict']))

    return {
        'product_fields': product_line_fields,
        'discount_fields': discount_line_fields,
        'orderbump_fields': orderbump_line_fields,
        'fkcart_fields': fkcart_upsell_line_fields,
        'last_ordered': ','.join(last_ordered_items)
    }

def update_active_campaign_product_fields(data):
    """
    Verwerkt de webhook data voor het updaten van Active Campaign product velden.
    
    Args:
        data: De geparsede webhook data
        
    Returns:
        Dict met status en resultaten
    """
    # Configuratie
    active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
    active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
    email = data.get('billing', {}).get('email')
    
    if not all([active_campaign_api_url, active_campaign_api_token, email]):
        raise ValueError("Ontbrekende configuratie of email")
    
    # Haal alle benodigde dictionaries op
    dicts = _get_required_dicts()
    
    # Verwerk line items
    processed_data = _process_line_items(data['line_items'], dicts)
    
    # Haal Active Campaign data op
    ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    ac_id = ac_data['contacts'][0]['id']
    field_values = get_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token)['fieldValues']
    
    # Bereid huidige velden voor
    current_fields = [
        {"field": item['field'], "value": item['value'], "id": item['id']}
        for item in field_values
    ]
    current_fields = sorted(current_fields, key=lambda x: int(x['field']))
    
    # Update velden
    all_new_fields = (
        processed_data['product_fields'] + 
        processed_data['discount_fields'] + 
        processed_data['orderbump_fields'] + 
        processed_data['fkcart_fields']
    )
    
    updated_fields, new_fields = update_field_values(current_fields, all_new_fields)
    updated_fields, new_fields = add_or_update_last_ordered_item(
        updated_fields, 
        new_fields, 
        processed_data['last_ordered']
    )
    
    # Push updates naar Active Campaign
    update_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token, updated_fields, new_fields)
    
    return {
        'status': 'success',
        'message': f"Product velden bijgewerkt voor {email}"
    }

def _get_desired_tags():
    """Retourneert de mapping van categorieën naar tag IDs."""
    return {
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

def _process_categories(category_list):
    """Verwerkt de categorieën volgens de business rules."""
    if 'Challenge' in category_list:
        category_list = [c for c in category_list if c not in ['Originals', 'Starter']]
        if 'Frisdrank' in category_list:
            category_list.remove('Frisdrank')
            category_list.append('a14_extra_frisdrank')
        if 'Starter' in category_list:
            category_list.remove('Starter')
            category_list.append('a14_extra_starter')
    elif 'Originals' in category_list:
        if 'Starter' in category_list:
            category_list.remove('Starter')
            category_list.append('a14_extra_starter')
        if 'Frisdrank' in category_list:
            category_list.remove('Frisdrank')
            category_list.append('a14_extra_frisdrank')
    elif 'Starter' in category_list and 'Frisdrank' in category_list:
            category_list.remove('Frisdrank')
            category_list.append('a3_extra_frisdrank')

    return list(set(category_list))

def add_product_tag_ac(data):
    """
    Verwerkt de webhook data voor het toevoegen van Active Campaign product tags.
    
    Args:
        data: De geparsede webhook data
        
    Returns:
        Dict met status en resultaten
    """
    # Configuratie
    active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
    active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
    email = data.get('billing', {}).get('email')
    
    if not all([active_campaign_api_url, active_campaign_api_token, email]):
        raise ValueError("Ontbrekende configuratie of email")
    
    # Haal Active Campaign ID op
    ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
    ac_id = ac_data['contacts'][0]['id']
    
    # Verwerk categorieën
    categories = get_category_one_dict()
    category_list = [
        get_key_from_product_id(item['product_id'], categories)
        for item in data['line_items']
        if get_key_from_product_id(item['product_id'], categories) is not None
    ]
    
    # Verwerk categorieën volgens business rules
    processed_categories = _process_categories(category_list)
    
    # Voeg tags toe
    desired_tags = _get_desired_tags()
    for category in processed_categories:
        if category in desired_tags:
            tag_id = desired_tags[category]
            add_tag_to_contact(
                [{"contact": ac_id, "tag": tag_id}],
                active_campaign_api_url,
                active_campaign_api_token
            )
    
    return {
        'status': 'success',
        'message': f"Tags bijgewerkt voor {email}"
    }

def update_ac_abo_field(data):
    """Update het abonnements veld in Active Campaign."""
    # Configuratie
    ac_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
    ac_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
    
    if not all([ac_api_url, ac_api_token]):
        raise ValueError("Ontbrekende Active Campaign configuratie")
    
    # Gewenste datapunten uit data halen
    email = data.get('billing', {}).get('email')
    if not email:
        raise ValueError("Geen email gevonden in data")

    # Active Campaign data ophalen
    ac_data = get_active_campaign_data(email, ac_api_url, ac_api_token)
    ac_id = ac_data['contacts'][0]['id']

    # Veld waarden ophalen
    field_values = get_active_campaign_fields(ac_id, ac_api_url, ac_api_token)

    # Huidige waarden ophalen
    desired_field = 21
    contact_id = None
    current_abo_value = None
    specific_abo_field_id = None

    for item in field_values['fieldValues']:
        if int(item['field']) == desired_field:
            contact_id = item['contact']
            current_abo_value = item['value']
            specific_abo_field_id = item['id']
            break

    # Controleren of veld bestaat
    if specific_abo_field_id:
        # Veld bestaat al, update het
        if current_abo_value and current_abo_value.isdigit():
            current_abo_value = int(current_abo_value)
        else:
            current_abo_value = 0

        new_abo_value = current_abo_value + 1

        updated_field = {
            "id": specific_abo_field_id,
            "field": str(desired_field),
            "value": str(new_abo_value)
        }
        update_active_campaign_fields(contact_id, ac_api_url, ac_api_token, updated_fields=[updated_field])
    else:
        # Veld bestaat niet, voeg het toe
        new_field = {
            "contact": ac_id,
            "field": str(desired_field),
            "value": '1'
        }
        update_active_campaign_fields(ac_id, ac_api_url, ac_api_token, new_fields=[new_field])
    
    return {
        'status': 'success',
        'message': f"Abonnements veld bijgewerkt voor {email}"
    }

def update_ac_abo_tag(data):
    """Voegt een abonnements tag toe in Active Campaign."""
    # Configuratie
    ac_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
    ac_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
    
    if not all([ac_api_url, ac_api_token]):
        raise ValueError("Ontbrekende Active Campaign configuratie")
    
    # Gewenste datapunten uit data halen
    email = data.get('billing', {}).get('email')
    if not email:
        raise ValueError("Geen email gevonden in data")

    # Active Campaign data ophalen
    ac_data = get_active_campaign_data(email, ac_api_url, ac_api_token)
    ac_id = ac_data['contacts'][0]['id']

    # Abonnements tag toevoegen
    abo_tag_id = 115
    tags = [{"contact": ac_id, "tag": abo_tag_id}]
    add_tag_to_contact(tags, ac_api_url, ac_api_token)
    
    return {
        'status': 'success',
        'message': f"Abonnements tag toegevoegd voor {email}"
    }

def add_originals_dummy_product(data):
    """Voegt een dummy product toe in WooCommerce."""
    # Configuratie
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )
    
    PRODUCT_ID = 107586
    
    try:
        contact = data.get('contact', {})
        email = contact.get('email')
        first_name = contact.get('first_name', '').strip() or ' '

        if not email:
            return {'success': False, 'error': 'Geen e-mailadres opgegeven'}
        
        # 1. Klant opzoeken
        customer_id = 0  # Standaard 0 voor gastbestellingen
        customers = wcapi.get("customers", params={"email": email}).json()
        if customers:
            customer_id = customers[0].get('id')
            
        # Product controleren
        product_response = wcapi.get(f"products/{PRODUCT_ID}")
        if not product_response.ok:
            return {'success': False, 'error': 'Product niet gevonden'}

        # Bestelling aanmaken
        order_data = {
            "customer_id": customer_id,  
            "billing": {
                "first_name": first_name,
                "email": email,
            },
            "line_items": [
                {
                    "product_id": PRODUCT_ID,
                    "quantity": 1
                }
            ],
            "status": "completed", 
            "set_paid": True,  
            "payment_method": "bacs", 
            "payment_method_title": "Automatische bestelling van ActiveCampaign"
        }

        order_response = wcapi.post("orders", data=order_data)
        if not order_response.ok:
            return {'success': False, 'error': 'Fout bij aanmaken bestelling'}

        return {
            'success': True,
            'order_id': order_response.json().get('id')
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}