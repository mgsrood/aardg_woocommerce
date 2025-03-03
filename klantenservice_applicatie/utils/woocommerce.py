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
    version="wc/v3"
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