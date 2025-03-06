import sqlite3
import os
import json
import logging
import traceback
from dotenv import load_dotenv

# Configureer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Laad environment variables
load_dotenv()

def get_subscription_status_display(status):
    """Vertaal status code naar leesbare tekst"""
    status_display = {
        'active': 'Actief',
        'on-hold': 'On-hold',
        'cancelled': 'Geannuleerd',
        'pending': 'In afwachting',
        'pending-cancel': 'Annulering in behandeling',
        'expired': 'Verlopen',
        'trash': 'Verwijderd'
    }
    return status_display.get(status, status)

def get_db_connection():
    """
    Maak een verbinding met de SQLite database.
    """
    db_path = os.getenv('SQLITE_DB_PATH', 'klantenservice_applicatie/data/woocommerce.db')
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Hiermee kunnen we resultaten als dictionaries opvragen
        logger.debug(f"Verbinding gemaakt met database: {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Fout bij verbinden met database: {str(e)}")
        return None

def search_subscriptions_by_id(subscription_id):
    """
    Zoek een abonnement op basis van ID.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        logger.info(f"Zoeken naar abonnement met ID: {subscription_id}")
        
        # Haal het abonnement op
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,))
        subscription_row = cursor.fetchone()
        
        if not subscription_row:
            logger.warning(f"Geen abonnement gevonden met ID: {subscription_id}")
            return {"error": f"Geen abonnement gevonden met ID: {subscription_id}", "status": 404}
        
        # Converteer naar dictionary
        subscription = dict(subscription_row)
        
        # Verwerk meta_data
        if subscription['meta_data']:
            try:
                subscription['meta_data'] = json.loads(subscription['meta_data'])
            except:
                subscription['meta_data'] = []
        
        # Voeg billing en shipping objecten toe voor compatibiliteit met WooCommerce API
        subscription['billing'] = {
            'first_name': subscription['billing_first_name'],
            'last_name': subscription['billing_last_name'],
            'email': subscription['billing_email'],
            'phone': subscription['billing_phone'],
            'address_1': subscription['billing_address_1'],
            'address_2': subscription['billing_address_2'],
            'postcode': subscription['billing_postcode'],
            'city': subscription['billing_city'],
            'country': subscription['billing_country']
        }
        
        # Voeg leesbare status toe
        subscription['status_display'] = {
            'active': 'Actief',
            'on-hold': 'On-hold',
            'cancelled': 'Geannuleerd',
            'pending': 'In afwachting'
        }.get(subscription['status'], subscription['status'])
        
        # Formateer datums
        if subscription.get('next_payment_date'):
            subscription['next_payment_date_formatted'] = subscription['next_payment_date'].split('T')[0] if 'T' in subscription['next_payment_date'] else subscription['next_payment_date']
        
        logger.info(f"Abonnement gevonden: {subscription_id}")
        return {"success": True, "data": [subscription]}
    
    except Exception as e:
        error_message = f"Fout bij zoeken naar abonnement: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def search_subscriptions_by_email(email):
    """
    Zoek abonnementen op basis van e-mailadres.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        logger.info(f"Zoeken naar abonnementen voor e-mail: {email}")
        
        # Haal abonnementen op
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subscriptions WHERE billing_email LIKE ?", (f"%{email}%",))
        subscription_ids = [row['id'] for row in cursor.fetchall()]
        
        if not subscription_ids:
            logger.warning(f"Geen abonnementen gevonden voor e-mail: {email}")
            return {"error": f"Geen abonnementen gevonden voor e-mail: {email}", "status": 404}
        
        # Haal details op voor elk abonnement
        subscriptions = []
        for subscription_id in subscription_ids:
            result = search_subscriptions_by_id(subscription_id)
            if result.get("success") and result.get("data"):
                subscriptions.extend(result["data"])
        
        logger.info(f"{len(subscriptions)} abonnementen gevonden voor e-mail: {email}")
        return {"success": True, "data": subscriptions}
    
    except Exception as e:
        error_message = f"Fout bij zoeken naar abonnementen: {str(e)}"
        logger.error(error_message)
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def search_subscriptions_by_name(name):
    """
    Zoek abonnementen op basis van voor- of achternaam.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        logger.info(f"Zoeken naar abonnementen voor naam: {name}")
        
        # Controleer of de naam mogelijk een volledige naam is (voornaam + achternaam)
        name_parts = name.strip().split()
        
        if len(name_parts) > 1:
            # Als er meerdere delen zijn, probeer te zoeken op voornaam + achternaam
            first_name = name_parts[0]
            # Combineer de rest als achternaam (voor namen met tussenvoegsel zoals "van der")
            last_name = ' '.join(name_parts[1:])
            
            logger.info(f"Zoeken op volledige naam: voornaam '{first_name}' en achternaam '{last_name}'")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM subscriptions 
                WHERE (billing_first_name LIKE ? AND billing_last_name LIKE ?)
                OR billing_first_name LIKE ? 
                OR billing_last_name LIKE ?
            """, (f"%{first_name}%", f"%{last_name}%", f"%{name}%", f"%{name}%"))
        else:
            # Zoek op enkele naam (alleen voornaam of alleen achternaam)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM subscriptions 
                WHERE billing_first_name LIKE ? OR billing_last_name LIKE ?
            """, (f"%{name}%", f"%{name}%"))
        
        subscription_ids = [row['id'] for row in cursor.fetchall()]
        
        if not subscription_ids:
            logger.warning(f"Geen abonnementen gevonden voor naam: {name}")
            return {"error": f"Geen abonnementen gevonden voor naam: {name}", "status": 404}
        
        # Haal details op voor elk abonnement
        subscriptions = []
        for subscription_id in subscription_ids:
            result = search_subscriptions_by_id(subscription_id)
            if result.get("success") and result.get("data"):
                subscriptions.extend(result["data"])
        
        logger.info(f"{len(subscriptions)} abonnementen gevonden voor naam: {name}")
        return {"success": True, "data": subscriptions}
    
    except Exception as e:
        error_message = f"Fout bij zoeken naar abonnementen op naam: {str(e)}"
        logger.error(error_message)
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def get_customer_id_by_email(email):
    """
    Haal klant ID op basis van e-mailadres.
    """
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT customer_id FROM subscriptions WHERE billing_email LIKE ?", (f"%{email}%",))
        row = cursor.fetchone()
        
        if row:
            return row['customer_id']
        else:
            return None
    
    except Exception as e:
        logger.error(f"Fout bij ophalen klant ID: {str(e)}")
        return None
    
    finally:
        conn.close()

def get_all_subscriptions(limit=100, offset=0):
    """
    Haal alle abonnementen op met paginering.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        logger.info(f"Ophalen van abonnementen (limit: {limit}, offset: {offset})")
        
        # Haal abonnementen op
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM subscriptions ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
        subscription_ids = [row['id'] for row in cursor.fetchall()]
        
        # Haal details op voor elk abonnement
        subscriptions = []
        for subscription_id in subscription_ids:
            result = search_subscriptions_by_id(subscription_id)
            if result.get("success") and result.get("data"):
                subscriptions.extend(result["data"])
        
        # Haal totaal aantal op
        cursor.execute("SELECT COUNT(*) as total FROM subscriptions")
        total = cursor.fetchone()['total']
        
        logger.info(f"{len(subscriptions)} abonnementen opgehaald (totaal: {total})")
        return {
            "success": True, 
            "data": subscriptions,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        error_message = f"Fout bij ophalen abonnementen: {str(e)}"
        logger.error(error_message)
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def get_orders_by_email(email):
    """Haal orders op voor een specifiek e-mailadres"""
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "Kan geen verbinding maken met de database"}
            
        cursor = conn.cursor()
        
        # Voeg index toe voor snellere zoekacties
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_email 
            ON orders(billing_email)
        """)
        
        # Zoek orders op basis van het e-mailadres met LIMIT
        cursor.execute("""
            SELECT o.*, 
                   o.billing_first_name || ' ' || o.billing_last_name as customer_name,
                   o.line_items as product_list,
                   o.created_date as date_created
            FROM orders o
            WHERE LOWER(o.billing_email) = LOWER(?)
            ORDER BY o.created_date DESC
            LIMIT 50  -- Beperk het aantal orders voor betere performance
        """, (email,))
        
        orders = []
        for row in cursor.fetchall():
            order_dict = dict(row)
            order_dict['line_items'] = []
            
            # Parse line_items JSON
            if order_dict['product_list']:
                try:
                    line_items = json.loads(order_dict['product_list'])
                    for item in line_items:
                        if isinstance(item['name'], list):
                            name = item['name'][0]
                        else:
                            name = item['name']
                            
                        if isinstance(item['quantity'], list):
                            quantity = item['quantity'][0]
                        else:
                            quantity = item['quantity']
                            
                        order_dict['line_items'].append({
                            'quantity': quantity,
                            'name': name
                        })
                except Exception as e:
                    logger.error(f"Fout bij parsen line_items JSON: {str(e)}")
            
            # Voeg leesbare status toe
            order_dict['status_display'] = {
                'completed': 'Voltooid',
                'processing': 'In behandeling',
                'on-hold': 'On-hold',
                'cancelled': 'Geannuleerd',
                'pending': 'In afwachting',
                'failed': 'Mislukt',
                'refunded': 'Terugbetaald'
            }.get(order_dict['status'], order_dict['status'])
            
            # Voeg geformatteerde datum toe
            if order_dict.get('date_created'):
                order_dict['date_created_formatted'] = order_dict['date_created'].split('T')[0] if 'T' in order_dict['date_created'] else order_dict['date_created']
            
            orders.append(order_dict)
            
        return {"success": True, "data": orders}
        
    except Exception as e:
        logger.error(f"Fout bij ophalen orders voor e-mail {email}: {str(e)}")
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def get_order_by_id(order_id):
    """
    Zoek een order op basis van ID.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        logger.info(f"Zoeken naar order met ID: {order_id}")
        
        # Haal de order op
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order_row = cursor.fetchone()
        
        if not order_row:
            logger.warning(f"Geen order gevonden met ID: {order_id}")
            return {"error": f"Geen order gevonden met ID: {order_id}", "status": 404}
        
        # Converteer naar dictionary
        order = dict(order_row)
        
        # Verwerk meta_data
        if order['meta_data']:
            try:
                order['meta_data'] = json.loads(order['meta_data'])
            except:
                order['meta_data'] = []
        
        # Voeg billing en shipping objecten toe voor compatibiliteit met WooCommerce API
        order['billing'] = {
            'first_name': order['billing_first_name'],
            'last_name': order['billing_last_name'],
            'email': order['billing_email'],
            'phone': order['billing_phone'],
            'address_1': order['billing_address_1'],
            'address_2': order['billing_address_2'],
            'postcode': order['billing_postcode'],
            'city': order['billing_city'],
            'country': order['billing_country']
        }
        
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
        
        logger.info(f"Order gevonden: {order_id}")
        return {"success": True, "data": order}
    
    except Exception as e:
        error_message = f"Fout bij zoeken naar order: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def search_orders_by_name(name):
    """
    Zoek orders op basis van voor- of achternaam.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        logger.info(f"Zoeken naar orders voor naam: {name}")
        
        # Controleer of de naam mogelijk een volledige naam is (voornaam + achternaam)
        name_parts = name.strip().split()
        
        if len(name_parts) > 1:
            # Als er meerdere delen zijn, probeer te zoeken op voornaam + achternaam
            first_name = name_parts[0]
            # Combineer de rest als achternaam (voor namen met tussenvoegsel zoals "van der")
            last_name = ' '.join(name_parts[1:])
            
            logger.info(f"Zoeken op volledige naam: voornaam '{first_name}' en achternaam '{last_name}'")
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders 
                WHERE (billing_first_name LIKE ? AND billing_last_name LIKE ?)
                OR billing_first_name LIKE ? 
                OR billing_last_name LIKE ?
                ORDER BY date_created DESC
            """, (f"%{first_name}%", f"%{last_name}%", f"%{name}%", f"%{name}%"))
        else:
            # Zoek op enkele naam (alleen voornaam of alleen achternaam)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM orders 
                WHERE billing_first_name LIKE ? OR billing_last_name LIKE ?
                ORDER BY date_created DESC
            """, (f"%{name}%", f"%{name}%"))
        
        orders_rows = cursor.fetchall()
        
        if not orders_rows:
            logger.warning(f"Geen orders gevonden voor naam: {name}")
            return {"error": f"Geen orders gevonden voor naam: {name}", "status": 404}
        
        # Converteer naar dictionaries
        orders = []
        for row in orders_rows:
            order = dict(row)
            
            # Verwerk meta_data
            if order['meta_data']:
                try:
                    order['meta_data'] = json.loads(order['meta_data'])
                except:
                    order['meta_data'] = []
            
            # Voeg billing object toe voor consistentie
            order['billing'] = {
                'first_name': order['billing_first_name'],
                'last_name': order['billing_last_name'],
                'email': order['billing_email'],
                'phone': order['billing_phone'],
                'address_1': order['billing_address_1'],
                'address_2': order['billing_address_2'],
                'postcode': order['billing_postcode'],
                'city': order['billing_city'],
                'country': order['billing_country']
            }
            
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
            
            orders.append(order)
        
        logger.info(f"{len(orders)} orders gevonden voor naam: {name}")
        return {"success": True, "data": orders}
    
    except Exception as e:
        error_message = f"Fout bij zoeken naar orders op naam: {str(e)}"
        logger.error(error_message)
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def get_subscription_statistics():
    """Haal statistieken op over abonnementen"""
    logger.info("Ophalen van abonnementsstatistieken")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Basisquery voor status counts
        cursor.execute("""
            SELECT status,
                   COUNT(*) as count,
                   SUM(total) as total_value
            FROM subscriptions
            GROUP BY status
        """)
        
        status_counts = []
        total_count = 0
        total_value = 0
        total_value_on_hold = 0
        
        for row in cursor.fetchall():
            status, count, value = row
            status_counts.append({
                'status': status,
                'status_display': get_subscription_status_display(status),
                'count': count
            })
            total_count += count
            if status == 'active':
                total_value = value if value is not None else 0
            elif status == 'on-hold':
                total_value_on_hold = value if value is not None else 0
        
        # Haal actieve abonnementen op
        cursor.execute("""
            SELECT COUNT(*) as count,
                   SUM(total) as total_value
            FROM subscriptions
            WHERE status = 'active'
        """)
        
        active_row = cursor.fetchone()
        active_count = active_row[0] if active_row[0] is not None else 0
        total_value_excl = active_row[1] if active_row[1] is not None else 0
        
        # Haal gepauzeerde abonnementen op
        cursor.execute("""
            SELECT COUNT(*) as count,
                   SUM(total) as total_value
            FROM subscriptions
            WHERE status = 'on-hold'
        """)
        
        on_hold_row = cursor.fetchone()
        on_hold_count = on_hold_row[0] if on_hold_row[0] is not None else 0
        total_value_on_hold = on_hold_row[1] if on_hold_row[1] is not None else 0
        
        conn.close()
        
        return {
            'success': True,
            'data': {
                'status_counts': status_counts,
                'total_count': total_count,
                'active_count': active_count,
                'total_value': total_value,
                'total_value_excl': total_value_excl,
                'total_value_on_hold': total_value_on_hold
            }
        }
    except Exception as e:
        logger.error(f"Fout bij ophalen abonnementsstatistieken: {str(e)}")
        return {
            'success': False,
            'error': f"Fout bij ophalen abonnementsstatistieken: {str(e)}"
        } 