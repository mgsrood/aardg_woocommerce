from active_campaign.utils import get_active_campaign_data, get_active_campaign_fields, update_active_campaign_fields, PRODUCT_TO_FIELD, CATEGORY_TO_FIELD, add_tag_to_contact
from utils.products import get_discount_dict, get_category_one_dict, get_base_unit_values, get_sku_dict, get_key_from_product_id, BASE_UNIT_VALUES
from active_campaign.utils import update_field_values, add_or_update_last_ordered_item
from woocommerce import API
from flask import request
import logging
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
        
        # Eerst SKU ophalen voor het product
        sku = get_key_from_product_id(product_id, dicts['sku_dict'])
        
        # Base value berekening op basis van SKU
        base_value = 0.0
        if sku:
            for base_unit, skus in BASE_UNIT_VALUES.items():
                if sku in skus:
                    try:
                        base_value = float(base_unit)
                        break
                    except (ValueError, TypeError):
                        logging.warning(f"Kon base_unit '{base_unit}' niet naar float converteren. Gebruik default 0.0.")
        else:
            logging.info(f"Geen SKU gevonden voor product ID {product_id} in sku_dict. Base value blijft 0.0.")
        
        total_value = int(base_value * quantity)

        # Product velden
        if sku and sku in PRODUCT_TO_FIELD:
            product_line_fields.append({
                "field": PRODUCT_TO_FIELD[sku],
                "value": total_value
            })
        elif not sku:
            logging.info(f"Product ID {product_id} niet gevonden in sku_dict, product field overgeslagen.")

        # Discount velden
        key_for_discount = get_key_from_product_id(product_id, dicts['discount_dict'])
        if key_for_discount and key_for_discount in CATEGORY_TO_FIELD:
            discount_line_fields.append({
                "field": CATEGORY_TO_FIELD[key_for_discount],
                "value": total_value
            })
        elif not key_for_discount:
            logging.info(f"Product ID {product_id} niet gevonden in discount_dict, discount field overgeslagen.")

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
        if sku:
            last_ordered_items.append("P_" + sku)
        else:
            logging.info(f"Product ID {product_id} niet gevonden in sku_dict, niet toegevoegd aan last_ordered_items.")

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
    """
    try:
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
        
        # Controleer of er daadwerkelijk velden zijn om bij te werken
        all_new_fields = (
            processed_data['product_fields'] + 
            processed_data['discount_fields'] + 
            processed_data['orderbump_fields'] + 
            processed_data['fkcart_fields']
        )
        
        if not all_new_fields:
            return {
                'status': 'warning',
                'message': f"Geen product velden bijgewerkt voor {email} - geen geldige SKU's gevonden in de bestelling"
            }
        
        # Haal Active Campaign data op
        ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
        if not ac_data.get('contacts'):
            logging.warning(f"Geen contact gevonden voor email: {email}")
            return {'status': 'error', 'message': 'Geen contact gevonden'}
            
        ac_id = ac_data['contacts'][0]['id']
        field_values = get_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token)['fieldValues']
        
        # Bereid huidige velden voor
        current_fields = [
            {"field": item['field'], "value": item['value'], "id": item['id']}
            for item in field_values
        ]
        current_fields = sorted(current_fields, key=lambda x: int(x['field']))
        
        # Update velden - deze functie retourneert nu alleen daadwerkelijk gewijzigde velden
        updated_fields, new_fields, changed_fields = update_field_values(current_fields, all_new_fields)
        updated_fields, new_fields, last_ordered_changed = add_or_update_last_ordered_item(
            updated_fields, 
            new_fields, 
            processed_data['last_ordered']
        )
        
        # Log wat er gaat gebeuren
        logging.info(f"Summary: {len(updated_fields)} existing fields to update, {len(new_fields)} new fields to create")
        
        # Alleen updaten als er daadwerkelijk iets is veranderd
        if len(updated_fields) > 0 or len(new_fields) > 0:
            # Push updates naar Active Campaign
            update_active_campaign_fields(ac_id, active_campaign_api_url, active_campaign_api_token, updated_fields, new_fields)
            
            return {
                'status': 'success',
                'message': f"Product velden bijgewerkt voor {email}",
                'existing_fields_updated': len(updated_fields),
                'new_fields_created': len(new_fields)
            }
        else:
            return {
                'status': 'info',
                'message': f"Geen wijzigingen nodig voor {email} - alle waarden zijn al correct"
            }
    except Exception as e:
        logging.error(f"Fout in update_active_campaign_product_fields: {str(e)}")
        return {'status': 'error', 'message': str(e)}

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
    
    if 'a14_extra_frisdrank' in category_list and 'Frisdrank' in category_list:
        category_list.remove('Frisdrank')
    if 'a3_extra_frisdrank' in category_list and 'Frisdrank' in category_list:
        category_list.remove('Frisdrank')
    if 'a14_extra_starter' in category_list and 'Starter' in category_list:
        category_list.remove('Starter')

    return list(set(category_list))

def add_product_tag_ac(data):
    """
    Verwerkt de webhook data voor het toevoegen van Active Campaign product tags.
    
    Args:
        data: De geparsede webhook data
        
    Returns:
        Dict met status en resultaten
    """
    try:
        # Configuratie
        active_campaign_api_url = os.getenv('ACTIVE_CAMPAIGN_API_URL')
        active_campaign_api_token = os.getenv('ACTIVE_CAMPAIGN_API_TOKEN')
        email = data.get('billing', {}).get('email')
        
        if not all([active_campaign_api_url, active_campaign_api_token, email]):
            raise ValueError("Ontbrekende configuratie of email")
        
        # Haal Active Campaign ID op
        ac_data = get_active_campaign_data(email, active_campaign_api_url, active_campaign_api_token)
        if not ac_data.get('contacts'):
            logging.warning(f"Geen contact gevonden voor email: {email}")
            return {'status': 'error', 'message': 'Geen contact gevonden'}
            
        ac_id = ac_data['contacts'][0]['id']
        
        # Verwerk categorieën
        categories = get_category_one_dict()
        category_list = []
        
        for item in data.get('line_items', []):
            product_id = item.get('product_id')
            if not product_id:
                logging.warning("Product ID ontbreekt in line item")
                continue
                
            category = get_key_from_product_id(product_id, categories)
            if category is not None:
                category_list.append(category)
            else:
                logging.info(f"Geen categorie gevonden voor product ID {product_id}")
        
        # Verwerk categorieën
        processed_categories = _process_categories(category_list)
        
        # Voeg tags toe
        desired_tags = _get_desired_tags()
        added_tags = []
        
        for category in processed_categories:
            if category in desired_tags:
                tag_id = desired_tags[category]
                try:
                    add_tag_to_contact(
                        [{"contact": ac_id, "tag": tag_id}],
                        active_campaign_api_url,
                        active_campaign_api_token
                    )
                    added_tags.append(category)
                except Exception as e:
                    logging.error(f"Fout bij toevoegen tag {category}: {str(e)}")
        
        return {
            'status': 'success',
            'message': f"Tags bijgewerkt voor {email}",
            'added_tags': added_tags
        }
    except Exception as e:
        logging.error(f"Fout in add_product_tag_ac: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def increase_ac_abo_field(data):
    """Update het abonnements veld in Active Campaign."""
    try:
        # Status controle toevoegen
        subscription_status = data.get('status')
        if subscription_status not in ['active', 'processing', 'on-hold']:
            logging.info(f"Subscription status '{subscription_status}' vereist geen verhoging van abo veld")
            return {
                'status': 'info',
                'message': f"Geen actie nodig voor status: {subscription_status}"
            }
            
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
        if not ac_data.get('contacts'):
            logging.warning(f"Geen contact gevonden voor email: {email}")
            return {'status': 'error', 'message': 'Geen contact gevonden'}
            
        ac_id = ac_data['contacts'][0]['id']

        # Veld waarden ophalen
        field_values = get_active_campaign_fields(ac_id, ac_api_url, ac_api_token)

        # Huidige waarden ophalen
        desired_field = 21
        contact_id = None
        current_abo_value = None
        specific_abo_field_id = None

        for item in field_values.get('fieldValues', []):
            if int(item.get('field', 0)) == desired_field:
                contact_id = item.get('contact')
                current_abo_value = item.get('value')
                specific_abo_field_id = item.get('id')
                break

        # Veilige conversie van current_abo_value
        try:
            current_abo_value = int(current_abo_value) if current_abo_value and current_abo_value.isdigit() else 0
        except (ValueError, TypeError):
            logging.warning(f"Ongeldige abo waarde gevonden: {current_abo_value}, reset naar 0")
            current_abo_value = 0

        new_abo_value = current_abo_value + 1

        # Controleren of veld bestaat
        if specific_abo_field_id:
            # Veld bestaat al, update het
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
            'message': f"Abonnements veld bijgewerkt voor {email}",
            'new_value': new_abo_value
        }
    except Exception as e:
        logging.error(f"Fout in update_ac_abo_field: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def decrease_ac_abo_field(data):
    """Verlaagt het abonnements veld in Active Campaign met 1."""
    try:
        # Status controle toevoegen
        subscription_status = data.get('status')
        if subscription_status not in ['expired', 'cancelled', 'pending-cancel']:
            logging.info(f"Subscription status '{subscription_status}' vereist geen verlaging van abo veld")
            return {
                'status': 'info',
                'message': f"Geen actie nodig voor status: {subscription_status}"
            }
        
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
        if not ac_data.get('contacts'):
            logging.warning(f"Geen contact gevonden voor email: {email}")
            return {'status': 'error', 'message': 'Geen contact gevonden'}
            
        ac_id = ac_data['contacts'][0]['id']

        # Veld waarden ophalen
        field_values = get_active_campaign_fields(ac_id, ac_api_url, ac_api_token)

        # Huidige waarden ophalen
        desired_field = 21
        contact_id = None
        current_abo_value = None
        specific_abo_field_id = None

        for item in field_values.get('fieldValues', []):
            if int(item.get('field', 0)) == desired_field:
                contact_id = item.get('contact')
                current_abo_value = item.get('value')
                specific_abo_field_id = item.get('id')
                break

        # Veilige conversie van current_abo_value
        try:
            current_abo_value = int(current_abo_value) if current_abo_value and current_abo_value.isdigit() else 0
        except (ValueError, TypeError):
            logging.warning(f"Ongeldige abo waarde gevonden: {current_abo_value}, reset naar 0")
            current_abo_value = 0

        new_abo_value = max(0, current_abo_value - 1) # Verlaag met 1, maar niet lager dan 0

        # Controleren of veld bestaat
        if specific_abo_field_id:
            # Veld bestaat al, update het
            updated_field = {
                "id": specific_abo_field_id,
                "field": str(desired_field),
                "value": str(new_abo_value)
            }
            update_active_campaign_fields(contact_id, ac_api_url, ac_api_token, updated_fields=[updated_field])
        else:
            # Veld bestaat niet, voeg het toe met waarde 0 (omdat we verlagen en het niet bestond)
            new_field = {
                "contact": ac_id,
                "field": str(desired_field),
                "value": '0' 
            }
            update_active_campaign_fields(ac_id, ac_api_url, ac_api_token, new_fields=[new_field])
        
        return {
            'status': 'success',
            'message': f"Abonnements veld verlaagd voor {email}",
            'new_value': new_abo_value
        }
    except Exception as e:
        logging.error(f"Fout in decrease_ac_abo_field: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def add_ac_abo_tag(data):
    """Voegt een abonnements tag toe in Active Campaign."""
    try:
        # Status controle toevoegen
        subscription_status = data.get('status')
        if subscription_status not in ['active', 'processing']:
            logging.info(f"Subscription status '{subscription_status}' vereist geen abonnements tag")
            return {
                'status': 'info',
                'message': f"Geen abonnements tag toegevoegd voor status: {subscription_status}"
            }
        
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
        if not ac_data.get('contacts'):
            logging.warning(f"Geen contact gevonden voor email: {email}")
            return {'status': 'error', 'message': 'Geen contact gevonden'}
            
        ac_id = ac_data['contacts'][0]['id']

        # Abonnements tag toevoegen
        abo_tag_id = 115
        tags = [{"contact": ac_id, "tag": abo_tag_id}]
        add_tag_to_contact(tags, ac_api_url, ac_api_token)
        
        return {
            'status': 'success',
            'message': f"Abonnements tag toegevoegd voor {email}"
        }
    except Exception as e:
        logging.error(f"Fout in add_ac_abo_tag: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def add_originals_dummy_product(data):
    """Voegt een dummy product toe in WooCommerce."""
    try:
        # Configuratie
        consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
        consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
        woocommerce_url = os.getenv('WOOCOMMERCE_URL')
        
        if not all([consumer_secret, consumer_key, woocommerce_url]):
            raise ValueError("Ontbrekende WooCommerce configuratie")
        
        wcapi = API(
            url=woocommerce_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=60
        )
        
        # Haal product ID op uit de request parameters
        product_id = request.args.get('product_id')
        try:
            PRODUCT_ID = int(product_id) if product_id else 107586
        except ValueError:
            logging.warning(f"Ongeldig product ID: {product_id}, gebruik default")
            PRODUCT_ID = 107586
        
        contact = data.get('contact', {})
        email = contact.get('email')
        first_name = contact.get('first_name', '').strip() or ' '

        if not email:
            logging.error("Geen e-mailadres opgegeven in contact data")
            return {'success': False, 'error': 'Geen e-mailadres opgegeven'}
        
        # 1. Klant opzoeken
        customer_id = 0  # Standaard 0 voor gastbestellingen
        try:
            customers = wcapi.get("customers", params={"email": email}).json()
            if customers:
                customer_id = customers[0].get('id')
        except Exception as e:
            logging.error(f"Fout bij ophalen klant: {str(e)}")
            
        # Product controleren
        try:
            product_response = wcapi.get(f"products/{PRODUCT_ID}")
            if not product_response.ok:
                logging.error(f"Product {PRODUCT_ID} niet gevonden")
                return {'success': False, 'error': 'Product niet gevonden'}
        except Exception as e:
            logging.error(f"Fout bij controleren product: {str(e)}")
            return {'success': False, 'error': 'Fout bij controleren product'}

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

        try:
            order_response = wcapi.post("orders", data=order_data)
            if not order_response.ok:
                logging.error(f"Fout bij aanmaken bestelling: {order_response.text}")
                return {'success': False, 'error': 'Fout bij aanmaken bestelling'}

            return {
                'success': True,
                'order_id': order_response.json().get('id')
            }
        except Exception as e:
            logging.error(f"Fout bij aanmaken bestelling: {str(e)}")
            return {'success': False, 'error': 'Fout bij aanmaken bestelling'}

    except Exception as e:
        logging.error(f"Fout in add_originals_dummy_product: {str(e)}")
        return {'success': False, 'error': str(e)}