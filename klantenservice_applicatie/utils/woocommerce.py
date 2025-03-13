from woocommerce import API
import os
from dotenv import load_dotenv
import json
import requests

load_dotenv()

wcapi = API(
    url=os.getenv('WOOCOMMERCE_URL'),
    consumer_key=os.getenv('WOOCOMMERCE_CONSUMER_KEY'),
    consumer_secret=os.getenv('WOOCOMMERCE_CONSUMER_SECRET'),
    version="wc/v3",
    timeout=30  # Verhoog timeout naar 30 seconden
)

def search_subscriptions_by_id(subscription_id):
    """
    Zoek een abonnement op basis van ID en haal verzendkosten op
    """
    try:
        print(f"Zoeken naar abonnement met ID: {subscription_id}")
        print(f"API URL: {os.getenv('WOOCOMMERCE_URL')}")
        
        # Haal specifiek abonnement op via ID
        response = wcapi.get(f"subscriptions/{subscription_id}")
        
        print(f"API Response status: {response.status_code}")
        print(f"API Response headers: {response.headers}")
        
        if response.status_code != 200:
            error_message = f"API Error: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
        
        try:
            subscription = response.json()
            
            # Voeg leesbare status toe
            subscription['status_display'] = {
                'active': 'Actief',
                'on-hold': 'On-hold',
                'cancelled': 'Geannuleerd',
                'pending': 'In afwachting'
            }.get(subscription['status'], subscription['status'])
            
            # Formateer datums
            if subscription.get('next_payment_date_gmt'):
                subscription['next_payment_date_formatted'] = subscription['next_payment_date_gmt'].split('T')[0]
            
            # Formateer vervaldatum als deze beschikbaar is
            if subscription.get('end_date_gmt'):
                subscription['end_date_formatted'] = subscription['end_date_gmt'].split('T')[0]
            
            # Verzendkosten verwerken
            shipping_lines = subscription.get('shipping_lines', [])
            total_shipping = 0
            shipping_methods = []
            
            for shipping in shipping_lines:
                total_shipping += float(shipping.get('total', 0))
                method = shipping.get('method_title', 'Onbekend')
                shipping_methods.append(method)
            
            subscription['shipping_total'] = total_shipping
            subscription['shipping_methods'] = shipping_methods
            
            return {"success": True, "data": [subscription]}  # Return als lijst voor consistentie met template
            
        except json.JSONDecodeError as e:
            error_message = f"Ongeldige JSON response: {str(e)}"
            print(error_message)
            print(f"Response content: {response.text}")
            return {"error": error_message, "status": 500}
    
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def get_order_by_id(order_id):
    """
    Haal een specifieke order op via de WooCommerce API.
    """
    try:
        print(f"Zoeken naar order met ID: {order_id}")
        print(f"API URL: {wcapi.url}orders/{order_id}")
        
        # Haal de order op
        response = wcapi.get(f"orders/{order_id}")
        
        if response.status_code != 200:
            error_message = f"Fout bij ophalen order: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
        
        # Decodeer de JSON-respons
        try:
            order = response.json()
            
            # Voeg leesbare status toe
            order['status_display'] = {
                'completed': 'Voltooid',
                'processing': 'In behandeling',
                'on-hold': 'On-hold',
                'cancelled': 'Geannuleerd',
                'pending': 'In afwachting',
                'failed': 'Mislukt',
                'refunded': 'Terugbetaald'
            }.get(order['status'], order['status'])
            
            # Formateer datums
            if order.get('date_created'):
                order['date_created_formatted'] = order['date_created'].split('T')[0] if 'T' in order['date_created'] else order['date_created']
            
            print(f"Order gevonden: {order_id}")
            return {"success": True, "data": order}
        
        except json.JSONDecodeError as e:
            error_message = f"Fout bij decoderen JSON: {str(e)}"
            print(error_message)
            return {"error": error_message, "status": 500}
    
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def get_orders_by_email(email):
    """
    Zoek orders op basis van e-mailadres via de WooCommerce API.
    """
    try:
        print(f"Zoeken naar orders voor e-mail: {email}")
        
        # Zoek orders met het opgegeven e-mailadres
        response = wcapi.get("orders", params={"search": email})
        
        if response.status_code != 200:
            error_message = f"Fout bij zoeken naar orders: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
        
        # Decodeer de JSON-respons
        try:
            orders = response.json()
            
            if not orders:
                print(f"Geen orders gevonden voor e-mail: {email}")
                return {"error": f"Geen orders gevonden voor e-mail: {email}", "status": 404}
            
            # Voeg leesbare status en geformatteerde datums toe
            for order in orders:
                order['status_display'] = {
                    'completed': 'Voltooid',
                    'processing': 'In behandeling',
                    'on-hold': 'On-hold',
                    'cancelled': 'Geannuleerd',
                    'pending': 'In afwachting',
                    'failed': 'Mislukt',
                    'refunded': 'Terugbetaald'
                }.get(order['status'], order['status'])
                
                if order.get('date_created'):
                    order['date_created_formatted'] = order['date_created'].split('T')[0] if 'T' in order['date_created'] else order['date_created']
            
            print(f"{len(orders)} orders gevonden voor e-mail: {email}")
            return {"success": True, "data": orders}
        
        except json.JSONDecodeError as e:
            error_message = f"Fout bij decoderen JSON: {str(e)}"
            print(error_message)
            return {"error": error_message, "status": 500}
    
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def search_orders_by_name(name):
    """
    Zoek orders op basis van naam via de WooCommerce API.
    """
    try:
        print(f"Zoeken naar orders voor naam: {name}")
        
        # Zoek orders met de opgegeven naam
        response = wcapi.get("orders", params={"search": name})
        
        if response.status_code != 200:
            error_message = f"Fout bij zoeken naar orders: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
        
        # Decodeer de JSON-respons
        try:
            orders = response.json()
            
            if not orders:
                print(f"Geen orders gevonden voor naam: {name}")
                return {"error": f"Geen orders gevonden voor naam: {name}", "status": 404}
            
            # Voeg leesbare status en geformatteerde datums toe
            for order in orders:
                order['status_display'] = {
                    'completed': 'Voltooid',
                    'processing': 'In behandeling',
                    'on-hold': 'On-hold',
                    'cancelled': 'Geannuleerd',
                    'pending': 'In afwachting',
                    'failed': 'Mislukt',
                    'refunded': 'Terugbetaald'
                }.get(order['status'], order['status'])
                
                if order.get('date_created'):
                    order['date_created_formatted'] = order['date_created'].split('T')[0] if 'T' in order['date_created'] else order['date_created']
            
            print(f"{len(orders)} orders gevonden voor naam: {name}")
            return {"success": True, "data": orders}
        
        except json.JSONDecodeError as e:
            error_message = f"Fout bij decoderen JSON: {str(e)}"
            print(error_message)
            return {"error": error_message, "status": 500}
    
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def get_subscription_statistics():
    """
    Haal statistieken op over abonnementen via de WooCommerce API, inclusief aantal per status en totale waarden.
    """
    try:
        print(f"Ophalen van abonnementsstatistieken via WooCommerce API")
        
        # Haal alle abonnementen op om statistieken te berekenen
        # We moeten alle pagina's ophalen om een volledig beeld te krijgen
        page = 1
        per_page = 100
        all_subscriptions = []
        status_counts = {}
        
        while True:
            # Haal een pagina met abonnementen op
            response = wcapi.get(
                "subscriptions",
                params={
                    'page': page,
                    'per_page': per_page
                }
            )
            
            if response.status_code != 200:
                print(f"Fout bij ophalen abonnementen: {response.status_code}")
                return {"error": f"Fout bij ophalen abonnementen: {response.status_code}", "status": response.status_code}
            
            subscriptions = response.json()
            if not subscriptions:
                break  # Geen abonnementen meer
                
            all_subscriptions.extend(subscriptions)
            page += 1
            
            # Stop als we minder dan per_page abonnementen hebben ontvangen (laatste pagina)
            if len(subscriptions) < per_page:
                break
        
        # Bereken statistieken
        for subscription in all_subscriptions:
            status = subscription.get('status', 'unknown')
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts[status] = 1
        
        # Voeg leesbare statusnamen toe
        status_display = {
            'active': 'Actief',
            'on-hold': 'On-hold',
            'cancelled': 'Geannuleerd',
            'pending': 'In afwachting',
            'pending-cancel': 'Annulering in behandeling',
            'expired': 'Verlopen',
            'trash': 'Verwijderd'
        }
        
        status_statistics = [
            {
                'status': status,
                'status_display': status_display.get(status, status),
                'count': count
            }
            for status, count in status_counts.items()
        ]
        
        # Bereken totale waarde van actieve abonnementen
        active_subscriptions = [s for s in all_subscriptions if s.get('status') == 'active']
        total_value_excl = sum(float(s.get('total', 0)) for s in active_subscriptions)
        total_shipping = sum(float(s.get('shipping_total', 0)) for s in active_subscriptions)
        total_value_incl = total_value_excl + total_shipping
        
        print(f"Abonnementsstatistieken opgehaald: {len(all_subscriptions)} totaal")
        return {
            "success": True,
            "data": {
                "status_counts": status_statistics,
                "total_count": len(all_subscriptions),
                "active_count": len(active_subscriptions),
                "total_value_excl": round(total_value_excl, 2),
                "total_shipping": round(total_shipping, 2),
                "total_value_incl": round(total_value_incl, 2)
            }
        }
    
    except Exception as e:
        error_message = f"Fout bij ophalen abonnementsstatistieken: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def update_subscription_status(subscription_id, new_status):
    """
    Update de status van een abonnement via de WooCommerce API.
    Mogelijke statussen: 'active', 'on-hold', 'cancelled', 'pending'
    """
    try:
        print(f"Ophalen huidige gegevens voor abonnement {subscription_id}")
        
        # Haal eerst de huidige gegevens op
        current_data = wcapi.get(f"subscriptions/{subscription_id}")
        if current_data.status_code != 200:
            error_message = f"Fout bij ophalen huidige gegevens: {current_data.status_code} - {current_data.text}"
            print(error_message)
            return {"error": error_message, "status": current_data.status_code}
            
        current_subscription = current_data.json()
        current_status = current_subscription.get('status', 'unknown')
        
        print(f"Updating subscription {subscription_id} van status: {current_status} naar: {new_status}")
        
        data = {
            'status': new_status
        }
        
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        
        if response.status_code != 200:
            error_message = f"Fout bij updaten abonnement: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
            
        subscription = response.json()
        
        # Voeg leesbare status toe voor zowel oude als nieuwe status
        status_display = {
            'active': 'Actief',
            'on-hold': 'On-hold',
            'cancelled': 'Geannuleerd',
            'pending': 'In afwachting'
        }
        
        subscription['previous_status'] = current_status
        subscription['previous_status_display'] = status_display.get(current_status, current_status)
        subscription['status_display'] = status_display.get(subscription['status'], subscription['status'])
        
        return {"success": True, "data": subscription}
        
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def update_subscription_billing_interval(subscription_id, billing_interval, billing_period='week'):
    """
    Update de factureringsinterval van een abonnement.
    billing_period kan 'day', 'week', 'month' of 'year' zijn.
    """
    try:
        print(f"Ophalen huidige gegevens voor abonnement {subscription_id}")
        
        # Haal eerst de huidige gegevens op
        current_data = wcapi.get(f"subscriptions/{subscription_id}")
        if current_data.status_code != 200:
            error_message = f"Fout bij ophalen huidige gegevens: {current_data.status_code} - {current_data.text}"
            print(error_message)
            return {"error": error_message, "status": current_data.status_code}
            
        current_subscription = current_data.json()
        current_interval = current_subscription.get('billing_interval', 'unknown')
        current_period = current_subscription.get('billing_period', 'unknown')
        
        print(f"Updating subscription {subscription_id} van interval: {current_interval} {current_period} naar: {billing_interval} {billing_period}")
        
        data = {
            'billing_interval': billing_interval,
            'billing_period': billing_period
        }
        
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        
        if response.status_code != 200:
            error_message = f"Fout bij updaten abonnement: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
            
        subscription = response.json()
        subscription['previous_billing_interval'] = current_interval
        subscription['previous_billing_period'] = current_period
            
        return {"success": True, "data": subscription}
        
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        return {"error": error_message, "status": 500}

def update_subscription_next_payment_date(subscription_id, next_payment_date, next_payment_time=None):
    """
    Update de volgende betaaldatum van een abonnement.
    next_payment_date moet in YYYY-MM-DD formaat zijn
    next_payment_time moet in HH:mm formaat zijn (optioneel, standaard 00:00)
    """
    try:
        # Als er geen tijd is opgegeven, gebruik dan 00:00
        time_str = next_payment_time if next_payment_time else "00:00"
        
        # Combineer datum en tijd
        next_payment_datetime = f"{next_payment_date} {time_str}:00"
        
        print(f"Updating subscription {subscription_id} next payment date to: {next_payment_datetime}")
        
        data = {
            'next_payment_date': next_payment_datetime
        }
        
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        
        if response.status_code != 200:
            error_message = f"Fout bij updaten abonnement: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
            
        return {"success": True, "data": response.json()}
        
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        return {"error": error_message, "status": 500}

def update_subscription_shipping_address(subscription_id, shipping_address):
    """
    Update het verzendadres van een abonnement.
    shipping_address moet een dictionary zijn met de volgende velden:
    first_name, last_name, address_1, address_2, city, state, postcode, country
    """
    try:
        print(f"Updating subscription {subscription_id} shipping address")
        print(f"Shipping address data: {shipping_address}")
        
        # Controleer of alle vereiste velden aanwezig zijn
        required_fields = ['first_name', 'last_name', 'address_1', 'city', 'postcode', 'country']
        missing_fields = [field for field in required_fields if not shipping_address.get(field)]
        
        if missing_fields:
            error_message = f"Ontbrekende verplichte velden voor verzendadres: {', '.join(missing_fields)}"
            print(error_message)
            return {"error": error_message, "status": 400}
        
        # Zorg ervoor dat optionele velden tenminste een lege string zijn
        optional_fields = ['company', 'address_2', 'state']
        for field in optional_fields:
            if field not in shipping_address or shipping_address[field] is None:
                shipping_address[field] = ''
        
        data = {
            'shipping': shipping_address
        }
        print(f"Request data: {data}")
        
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code != 200:
            error_message = f"Fout bij updaten abonnement: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
            
        return {"success": True, "data": response.json()}
        
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def update_subscription_billing_address(subscription_id, billing_address):
    """
    Update het factuuradres van een abonnement.
    billing_address moet een dictionary zijn met de volgende velden:
    first_name, last_name, address_1, address_2, city, state, postcode, country, email, phone
    """
    try:
        print(f"Updating subscription {subscription_id} billing address")
        print(f"Billing address data: {billing_address}")
        
        # Controleer of alle vereiste velden aanwezig zijn
        required_fields = ['first_name', 'last_name', 'address_1', 'city', 'postcode', 'country', 'email']
        missing_fields = [field for field in required_fields if not billing_address.get(field)]
        
        if missing_fields:
            error_message = f"Ontbrekende verplichte velden voor factuuradres: {', '.join(missing_fields)}"
            print(error_message)
            return {"error": error_message, "status": 400}
        
        # Zorg ervoor dat optionele velden tenminste een lege string zijn
        optional_fields = ['company', 'address_2', 'state', 'phone']
        for field in optional_fields:
            if field not in billing_address or billing_address[field] is None:
                billing_address[field] = ''
        
        data = {
            'billing': billing_address
        }
        print(f"Request data: {data}")
        
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code != 200:
            error_message = f"Fout bij updaten factuuradres: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
            
        return {"success": True, "data": response.json()}
        
    except Exception as e:
        error_message = f"Onverwachte fout: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def get_subscription_products():
    """
    Haalt alle producten op die als abonnement zijn gemarkeerd in WooCommerce.
    """
    try:
        print(f"Ophalen van abonnementsproducten via WooCommerce API")
        
        # Haal producten op met type 'subscription'
        response = wcapi.get("products", params={
            "type": "subscription",
            "status": "publish",
            "per_page": 100  # Maximaal aantal per pagina
        })  # Verwijder de timeout parameter
        
        print(f"WooCommerce API response status: {response.status_code}")
        
        if response.status_code != 200:
            error_message = f"Fout bij ophalen producten: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
        
        products = response.json()
        print(f"Aantal opgehaalde producten: {len(products)}")
        
        # Verwerk de producten voor eenvoudiger gebruik
        formatted_products = []
        for product in products:
            try:
                formatted_product = {
                    'id': product['id'],
                    'name': product['name'],
                    'price': product.get('price', '0.00'),
                    'regular_price': product.get('regular_price', '0.00'),
                    'description': product.get('short_description', ''),
                    'sku': product.get('sku', ''),
                    'stock_status': product.get('stock_status', 'instock'),
                    'stock_quantity': product.get('stock_quantity'),
                    'images': [img['src'] for img in product.get('images', [])],
                    'attributes': product.get('attributes', [])
                }
                formatted_products.append(formatted_product)
            except Exception as e:
                print(f"Fout bij verwerken product {product.get('id')}: {str(e)}")
        
        print(f"{len(formatted_products)} abonnementsproducten opgehaald en verwerkt")
        return {"success": True, "data": formatted_products}
        
    except Exception as e:
        error_message = f"Onverwachte fout bij ophalen producten: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}

def update_subscription_expiry_date(subscription_id, expiry_date, expiry_time=None):
    """
    Update de vervaldatum van een abonnement.
    expiry_date moet in YYYY-MM-DD formaat zijn
    expiry_time moet in HH:mm formaat zijn (optioneel, standaard 00:00)
    """
    try:
        # Als er geen tijd is opgegeven, gebruik dan 00:00
        time_str = expiry_time if expiry_time else "00:00"
        
        # Combineer datum en tijd
        expiry_datetime = f"{expiry_date} {time_str}:00"
        
        print(f"Updating subscription {subscription_id} expiry date to: {expiry_datetime}")
        
        data = {
            'end_date': expiry_datetime
        }
        
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        
        if response.status_code != 200:
            error_message = f"Fout bij updaten vervaldatum abonnement: {response.status_code} - {response.text}"
            print(error_message)
            return {"error": error_message, "status": response.status_code}
            
        return {"success": True, "data": response.json()}
        
    except Exception as e:
        error_message = f"Onverwachte fout bij updaten vervaldatum: {str(e)}"
        print(error_message)
        return {"error": error_message, "status": 500}