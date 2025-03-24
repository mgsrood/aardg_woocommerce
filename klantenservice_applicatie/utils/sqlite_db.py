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
        cursor.execute("""
            SELECT s.*, 
                   s.billing_first_name || ' ' || s.billing_last_name as customer_name
            FROM subscriptions s
            WHERE s.id = ?
        """, (subscription_id,))
        
        subscription_row = cursor.fetchone()
        
        if not subscription_row:
            logger.warning(f"Geen abonnement gevonden met ID: {subscription_id}")
            return {"error": f"Geen abonnement gevonden met ID: {subscription_id}", "status": 404}
        
        # Converteer naar dictionary
        subscription = dict(subscription_row)
        
        # Haal de laatste order datum op voor het e-mailadres
        if subscription.get('billing_email'):
            last_order_date = get_last_order_date_by_email(subscription['billing_email'])
            if last_order_date:
                subscription['last_order_date'] = last_order_date
                subscription['last_order_date_formatted'] = last_order_date.split('T')[0] if 'T' in last_order_date else last_order_date
        
        # Voeg billing object toe voor compatibiliteit met WooCommerce API
        subscription['billing'] = {
            'first_name': subscription.get('billing_first_name', ''),
            'last_name': subscription.get('billing_last_name', ''),
            'email': subscription.get('billing_email', ''),
            'phone': subscription.get('billing_phone', ''),
            'address_1': subscription.get('billing_address_1', ''),
            'address_2': subscription.get('billing_address_2', ''),
            'postcode': subscription.get('billing_postcode', ''),
            'city': subscription.get('billing_city', ''),
            'country': subscription.get('billing_country', ''),
            'company': subscription.get('billing_company', '')
        }
        
        # Voeg leesbare status toe
        subscription['status_display'] = {
            'active': 'Actief',
            'on-hold': 'Gepauzeerd',
            'cancelled': 'Geannuleerd',
            'pending': 'In afwachting',
            'expired': 'Verlopen'
        }.get(subscription.get('status', ''), subscription.get('status', ''))
        
        # Formateer datums
        if subscription.get('start_date'):
            subscription['start_date_formatted'] = subscription['start_date'].split('T')[0] if 'T' in subscription['start_date'] else subscription['start_date']
        
        if subscription.get('next_payment_date'):
            subscription['next_payment_date_formatted'] = subscription['next_payment_date'].split('T')[0] if 'T' in subscription['next_payment_date'] else subscription['next_payment_date']
        
        logger.info(f"Abonnement gevonden: {subscription['id']}")
        return {"success": True, "data": [subscription]}
        
    except Exception as e:
        error_message = f"Fout bij zoeken naar abonnement: {str(e)}"
        logger.error(error_message)
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
        cursor.execute("""
            SELECT s.*, 
                   s.billing_first_name || ' ' || s.billing_last_name as customer_name
            FROM subscriptions s
            WHERE s.billing_email LIKE ?
        """, (f"%{email}%",))
        
        subscriptions = []
        for row in cursor.fetchall():
            subscription = dict(row)
            
            # Haal de laatste order datum op voor het e-mailadres
            if subscription.get('billing_email'):
                last_order_date = get_last_order_date_by_email(subscription['billing_email'])
                if last_order_date:
                    subscription['last_order_date'] = last_order_date
                    subscription['last_order_date_formatted'] = last_order_date.split('T')[0] if 'T' in last_order_date else last_order_date
            
            # Voeg billing object toe voor compatibiliteit met WooCommerce API
            subscription['billing'] = {
                'first_name': subscription.get('billing_first_name', ''),
                'last_name': subscription.get('billing_last_name', ''),
                'email': subscription.get('billing_email', ''),
                'phone': subscription.get('billing_phone', ''),
                'address_1': subscription.get('billing_address_1', ''),
                'address_2': subscription.get('billing_address_2', ''),
                'postcode': subscription.get('billing_postcode', ''),
                'city': subscription.get('billing_city', ''),
                'country': subscription.get('billing_country', ''),
                'company': subscription.get('billing_company', '')
            }
            
            # Voeg leesbare status toe
            subscription['status_display'] = {
                'active': 'Actief',
                'on-hold': 'Gepauzeerd',
                'cancelled': 'Geannuleerd',
                'pending': 'In afwachting',
                'expired': 'Verlopen'
            }.get(subscription.get('status', ''), subscription.get('status', ''))
            
            # Formateer datums
            if subscription.get('start_date'):
                subscription['start_date_formatted'] = subscription['start_date'].split('T')[0] if 'T' in subscription['start_date'] else subscription['start_date']
            
            if subscription.get('next_payment_date'):
                subscription['next_payment_date_formatted'] = subscription['next_payment_date'].split('T')[0] if 'T' in subscription['next_payment_date'] else subscription['next_payment_date']
            
            subscriptions.append(subscription)
        
        if not subscriptions:
            logger.warning(f"Geen abonnementen gevonden voor e-mail: {email}")
            return {"error": f"Geen abonnementen gevonden voor e-mail: {email}", "status": 404}
        
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

def get_all_subscriptions(limit=None, offset=None):
    """
    Haal alle abonnementen op met optionele paginering.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database"}
    
    try:
        cursor = conn.cursor()
        
        # Basis query
        query = """
            SELECT s.*, 
                   s.billing_first_name || ' ' || s.billing_last_name as customer_name
            FROM subscriptions s
        """
        
        # Voeg ORDER BY en LIMIT/OFFSET toe als ze zijn opgegeven
        query += " ORDER BY s.id DESC"
        if limit is not None:
            query += " LIMIT ?"
            if offset is not None:
                query += " OFFSET ?"
        
        # Voer de query uit
        if limit is not None and offset is not None:
            cursor.execute(query, (limit, offset))
        elif limit is not None:
            cursor.execute(query, (limit,))
        else:
            cursor.execute(query)
        
        subscriptions = []
        for row in cursor.fetchall():
            subscription = dict(row)
            
            # Haal de laatste order datum op voor het e-mailadres
            if subscription.get('billing_email'):
                last_order_date = get_last_order_date_by_email(subscription['billing_email'])
                if last_order_date:
                    subscription['last_order_date'] = last_order_date
                    subscription['last_order_date_formatted'] = last_order_date.split('T')[0] if 'T' in last_order_date else last_order_date
            
            subscriptions.append(subscription)
        
        # Haal totaal aantal abonnementen op
        cursor.execute("SELECT COUNT(*) as total FROM subscriptions")
        total = cursor.fetchone()['total']
        
        return {
            "success": True,
            "data": subscriptions,
            "total": total
        }
        
    except Exception as e:
        logger.error(f"Fout bij ophalen abonnementen: {str(e)}")
        return {"error": str(e)}
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
        
        # Verwerk meta_data als het bestaat
        if order.get('meta_data'):
            try:
                order['meta_data'] = json.loads(order['meta_data'])
            except:
                order['meta_data'] = []
        else:
            order['meta_data'] = []
        
        # Voeg billing en shipping objecten toe voor compatibiliteit met WooCommerce API
        order['billing'] = {
            'first_name': order.get('billing_first_name', ''),
            'last_name': order.get('billing_last_name', ''),
            'email': order.get('billing_email', ''),
            'phone': order.get('billing_phone', ''),
            'address_1': order.get('billing_address_1', ''),
            'address_2': order.get('billing_address_2', ''),
            'postcode': order.get('billing_postcode', ''),
            'city': order.get('billing_city', ''),
            'country': order.get('billing_country', ''),
            'company': order.get('billing_company', '')
        }
        
        order['shipping'] = {
            'first_name': order.get('shipping_first_name', ''),
            'last_name': order.get('shipping_last_name', ''),
            'address_1': order.get('shipping_address_1', ''),
            'address_2': order.get('shipping_address_2', ''),
            'postcode': order.get('shipping_postcode', ''),
            'city': order.get('shipping_city', ''),
            'country': order.get('shipping_country', ''),
            'company': order.get('shipping_company', '')
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
        }.get(order.get('status', ''), order.get('status', ''))
        
        # Parse line_items JSON als het bestaat
        if order.get('line_items'):
            try:
                order['line_items'] = json.loads(order['line_items'])
            except:
                order['line_items'] = []
        else:
            order['line_items'] = []
        
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
        
        # Maak de zoekterm case-insensitive en verwijder extra spaties
        search_term = name.strip().lower()
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM orders 
            WHERE LOWER(billing_first_name || ' ' || billing_last_name) LIKE ?
            OR LOWER(billing_first_name) LIKE ?
            OR LOWER(billing_last_name) LIKE ?
            ORDER BY created_date DESC
            LIMIT 50
        """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
        
        orders_rows = cursor.fetchall()
        
        if not orders_rows:
            logger.warning(f"Geen orders gevonden voor naam: {name}")
            return {"error": f"Geen orders gevonden voor naam: {name}", "status": 404}
        
        # Converteer naar dictionaries
        orders = []
        for row in orders_rows:
            order = dict(row)
            
            # Verwerk meta_data
            if order.get('meta_data'):
                try:
                    order['meta_data'] = json.loads(order['meta_data'])
                except:
                    order['meta_data'] = []
            
            # Parse line_items JSON als het bestaat
            if order.get('line_items'):
                try:
                    order['line_items'] = json.loads(order['line_items'])
                except:
                    order['line_items'] = []
            
            # Voeg billing object toe voor consistentie
            order['billing'] = {
                'first_name': order.get('billing_first_name', ''),
                'last_name': order.get('billing_last_name', ''),
                'email': order.get('billing_email', ''),
                'phone': order.get('billing_phone', ''),
                'address_1': order.get('billing_address_1', ''),
                'address_2': order.get('billing_address_2', ''),
                'postcode': order.get('billing_postcode', ''),
                'city': order.get('billing_city', ''),
                'country': order.get('billing_country', '')
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
            }.get(order.get('status', ''), order.get('status', ''))
            
            # Formateer datums
            if order.get('created_date'):
                order['date_created_formatted'] = order['created_date'].split('T')[0] if 'T' in order['created_date'] else order['created_date']
            
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

def init_db():
    """Initialiseer de database tabellen"""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Maak order_margin_data tabel
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_margin_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                margin DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id)
            )
        """)
        
        # Voeg shipping kolommen toe aan orders tabel
        shipping_columns = [
            "shipping_first_name TEXT",
            "shipping_last_name TEXT",
            "shipping_address_1 TEXT",
            "shipping_address_2 TEXT",
            "shipping_postcode TEXT",
            "shipping_city TEXT",
            "shipping_country TEXT",
            "shipping_company TEXT"
        ]
        
        for column in shipping_columns:
            try:
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column};")
            except sqlite3.OperationalError:
                # Kolom bestaat mogelijk al
                continue
        
        # Voeg Monta order tracking toe aan orders tabel
        monta_columns = [
            "monta_order_id TEXT",
            "monta_order_status TEXT",
            "monta_order_created_at TIMESTAMP",
            "monta_shipment_date DATE"
        ]
        
        for column in monta_columns:
            try:
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column};")
            except sqlite3.OperationalError:
                # Kolom bestaat mogelijk al
                continue
        
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Fout bij initialiseren database: {str(e)}")
        return False
    finally:
        conn.close()

def update_order_monta_status(order_id, monta_order_id, status, shipment_date=None):
    """Update de Monta order status voor een order"""
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database"}
        
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE orders 
            SET monta_order_id = ?, 
                monta_order_status = ?,
                monta_order_created_at = CURRENT_TIMESTAMP,
                monta_shipment_date = ?
            WHERE id = ?
        """, (monta_order_id, status, shipment_date, order_id))
        
        conn.commit()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def get_last_order_date_by_email(email):
    """Haal de datum van de laatste order op voor een specifiek e-mailadres"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        
        # Haal de datum van de laatste order op
        cursor.execute("""
            SELECT created_date
            FROM orders
            WHERE LOWER(billing_email) = LOWER(?)
            ORDER BY created_date DESC
            LIMIT 1
        """, (email,))
        
        row = cursor.fetchone()
        if row and row['created_date']:
            return row['created_date']
            
        return None
        
    except Exception as e:
        logger.error(f"Fout bij ophalen laatste order datum voor e-mail {email}: {str(e)}")
        return None
    finally:
        if conn:
            conn.close() 