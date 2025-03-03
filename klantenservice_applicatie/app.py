from flask import Flask, render_template, request, redirect, url_for, jsonify
from utils.woocommerce import search_subscriptions_by_id as wc_search_by_id, get_order_by_id as wc_get_order_by_id
from utils.woocommerce import get_subscription_statistics as wc_get_subscription_statistics
from utils.sqlite_db import search_subscriptions_by_id as db_search_by_id
from utils.sqlite_db import search_subscriptions_by_email, get_all_subscriptions, get_orders_by_email, search_subscriptions_by_name
from utils.sqlite_db import get_order_by_id as db_get_order_by_id, search_orders_by_name, get_subscription_statistics
from utils.bigquery_import import get_order_margin
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Configureer logging
logger = logging.getLogger(__name__)

# Laad environment variables
load_dotenv()

app = Flask(__name__)

# Bepaal welke databron te gebruiken
USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'

def get_db_connection():
    """Maak een database connectie"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'woocommerce.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Fout bij maken database connectie: {str(e)}")
        return None

def get_recent_orders(limit=5):
    """Haal de meest recente orders op"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.*, 
                   o.billing_first_name || ' ' || o.billing_last_name as customer_name,
                   GROUP_CONCAT(omd.quantity || 'x ' || omd.base_product, CHAR(10)) as product_list
            FROM orders o
            LEFT JOIN order_margin_data omd ON o.id = omd.order_id
            GROUP BY o.id
            ORDER BY o.date_created DESC 
            LIMIT ?
        """, (limit,))
        
        orders = []
        for row in cursor.fetchall():
            order_dict = dict(row)
            order_dict['line_items'] = []
            
            if order_dict['product_list']:
                for product in order_dict['product_list'].split('\n'):
                    if product:
                        qty, name = product.split('x ', 1)
                        order_dict['line_items'].append({
                            'quantity': int(qty),
                            'name': name.strip()
                        })
            
            orders.append(order_dict)
            
        return orders
    except Exception as e:
        logger.error(f"Fout bij ophalen recente orders: {str(e)}")
        return []
    finally:
        conn.close()

def get_recent_subscriptions(limit=5):
    """Haal de meest recente abonnementen op"""
    if USE_SQLITE:
        result = get_all_subscriptions(limit=limit)
        if 'success' in result and result['success']:
            return result.get('data', [])
    return []

def get_monthly_order_stats():
    """Haal statistieken op voor orders van deze maand"""
    conn = get_db_connection()
    if not conn:
        return {"count": 0, "total": 0}
    
    try:
        cursor = conn.cursor()
        first_day = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        last_day = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT COUNT(*) as count, SUM(total) as total
            FROM orders 
            WHERE date_created >= ? AND date_created < ?
        """, (first_day, last_day))
        
        result = cursor.fetchone()
        return {
            "count": result['count'] if result['count'] else 0,
            "total": result['total'] if result['total'] else 0
        }
    except Exception as e:
        logger.error(f"Fout bij ophalen maandelijkse orderstatistieken: {str(e)}")
        return {"count": 0, "total": 0}
    finally:
        conn.close()

@app.route('/')
def index():
    """Homepage met zoekformulier en statistieken"""
    view_type = request.args.get('view', 'subscriptions')  # 'subscriptions' of 'orders'
    
    if view_type == 'subscriptions':
        # Haal abonnementsstatistieken op
        subscription_stats = None
        if USE_SQLITE:
            stats_result = get_subscription_statistics()
            if 'success' in stats_result and stats_result['success']:
                subscription_stats = stats_result['data']
        
        # Haal recente abonnementen op
        recent_subscriptions = get_recent_subscriptions(5)
        
        return render_template('index.html',
                             view_type=view_type,
                             subscription_stats=subscription_stats,
                             recent_subscriptions=recent_subscriptions)
    else:
        # Haal orderstatistieken op
        order_stats = get_monthly_order_stats()
        
        # Haal recente orders op
        recent_orders = get_recent_orders(5)
        
        return render_template('index.html',
                             view_type=view_type,
                             order_stats=order_stats,
                             recent_orders=recent_orders)

@app.route('/search')
def search():
    """Zoek abonnement of order op ID, e-mail of naam"""
    search_type = request.args.get('type', 'subscription')
    
    if search_type == 'subscription':
        return search_subscriptions()
    elif search_type == 'order':
        return search_orders()
    else:
        return render_template('index.html', error="Ongeldig zoektype. Kies 'subscription' of 'order'.")

@app.route('/search')
def search_subscriptions():
    """Zoek abonnement op ID, e-mail of naam"""
    subscription_id = request.args.get('subscription_id')
    email = request.args.get('email')
    name = request.args.get('name')
    
    # Haal statistieken op voor de template
    subscription_stats = None
    if USE_SQLITE:
        stats_result = get_subscription_statistics()
        if 'success' in stats_result and stats_result['success']:
            subscription_stats = stats_result['data']
    
    if subscription_id:
        try:
            subscription_id = int(subscription_id)
            if USE_SQLITE:
                result = db_search_by_id(subscription_id)
            else:
                result = wc_search_by_id(subscription_id)
            
            if 'error' in result:
                return render_template('index.html', 
                                    error=result['error'],
                                    view_type='subscriptions',
                                    subscription_stats=subscription_stats)
            
            subscriptions = result.get('data', [])
            return render_template('index.html', 
                                subscriptions=subscriptions,
                                view_type='subscriptions',
                                subscription_stats=subscription_stats)
        except ValueError:
            return render_template('index.html', 
                                error="Ongeldig abonnements-ID. Voer een geldig nummer in.",
                                view_type='subscriptions',
                                subscription_stats=subscription_stats)
    
    elif email:
        if USE_SQLITE:
            result = search_subscriptions_by_email(email)
        else:
            # Fallback naar WooCommerce API als SQLite niet wordt gebruikt
            from utils.woocommerce import search_subscriptions_by_email as wc_search_by_email
            result = wc_search_by_email(email)
        
        if 'error' in result:
            return render_template('index.html', 
                                error=result['error'],
                                view_type='subscriptions',
                                subscription_stats=subscription_stats)
        
        subscriptions = result.get('data', [])
        return render_template('index.html', 
                            subscriptions=subscriptions,
                            view_type='subscriptions',
                            subscription_stats=subscription_stats)
    
    elif name:
        if USE_SQLITE:
            result = search_subscriptions_by_name(name)
            
            if 'error' in result:
                return render_template('index.html', 
                                    error=result['error'],
                                    view_type='subscriptions',
                                    subscription_stats=subscription_stats)
            
            subscriptions = result.get('data', [])
            return render_template('index.html', 
                                subscriptions=subscriptions,
                                view_type='subscriptions',
                                subscription_stats=subscription_stats)
        else:
            # Naam zoeken wordt alleen ondersteund in SQLite modus
            return render_template('index.html', 
                                error="Zoeken op naam wordt alleen ondersteund in SQLite modus.",
                                view_type='subscriptions',
                                subscription_stats=subscription_stats)
    
    return render_template('index.html', 
                         subscription_stats=subscription_stats,
                         view_type='subscriptions')

def search_orders():
    """Zoek order op ID, e-mail of naam"""
    order_id = request.args.get('order_id')
    email = request.args.get('email')
    name = request.args.get('name')
    
    # Haal orderstatistieken op voor de template
    order_stats = get_monthly_order_stats()
    recent_orders = get_recent_orders(5)
    
    if order_id:
        try:
            order_id = int(order_id)
            
            if USE_SQLITE:
                result = db_get_order_by_id(order_id)
            else:
                result = wc_get_order_by_id(order_id)
                
            if 'error' in result:
                return render_template('index.html', 
                                    error=result['error'],
                                    view_type='orders',
                                    order_stats=order_stats,
                                    recent_orders=recent_orders)
            
            # Voor een enkele order, maak een lijst met één item
            if 'data' in result and not isinstance(result['data'], list):
                orders = [result['data']]
            else:
                orders = result.get('data', [])
                
            return render_template('index.html', 
                                orders=orders,
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
            
        except ValueError:
            return render_template('index.html', 
                                error="Ongeldig order-ID. Voer een geldig nummer in.",
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
    
    elif email:
        if USE_SQLITE:
            result = get_orders_by_email(email)
        else:
            # Fallback naar WooCommerce API als SQLite niet wordt gebruikt
            from utils.woocommerce import get_orders_by_email as wc_get_orders_by_email
            result = wc_get_orders_by_email(email)
            
        if 'error' in result:
            return render_template('index.html', 
                                error=result['error'],
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
        
        orders = result.get('data', [])
        return render_template('index.html', 
                            orders=orders,
                            view_type='orders',
                            order_stats=order_stats,
                            recent_orders=recent_orders)
    
    elif name:
        if USE_SQLITE:
            result = search_orders_by_name(name)
            
            if 'error' in result:
                return render_template('index.html', 
                                    error=result['error'],
                                    view_type='orders',
                                    order_stats=order_stats,
                                    recent_orders=recent_orders)
            
            orders = result.get('data', [])
            return render_template('index.html', 
                                orders=orders,
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
        else:
            # Naam zoeken wordt alleen ondersteund in SQLite modus
            return render_template('index.html', 
                                error="Zoeken op naam wordt alleen ondersteund in SQLite modus.",
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
    
    return render_template('index.html', 
                         view_type='orders',
                         order_stats=order_stats,
                         recent_orders=recent_orders)

@app.route('/subscription/<int:subscription_id>')
def subscription_details(subscription_id):
    """Toon details van een specifiek abonnement"""
    # Altijd WooCommerce API gebruiken voor volledige details
    from utils.woocommerce import search_subscriptions_by_id as wc_search_by_id
    result = wc_search_by_id(subscription_id)
    
    if 'error' in result:
        return render_template('subscription_details.html', error=result['error'])
    
    subscription = result.get('data', [])[0] if result.get('data') else None
    
    # Haal orders op voor het e-mailadres als we SQLite gebruiken
    orders = []
    if USE_SQLITE and subscription and subscription.get('billing', {}).get('email'):
        email = subscription['billing']['email']
        orders_result = get_orders_by_email(email)
        if 'success' in orders_result:
            orders = orders_result.get('data', [])
    
    # Altijd use_woocommerce op True zetten
    return render_template('subscription_details.html', subscription=subscription, orders=orders, use_woocommerce=True)

@app.route('/order/<int:order_id>')
def order_details(order_id):
    """Toon details van een specifieke order"""
    # Gebruik altijd de WooCommerce API voor orderdetails
    result = wc_get_order_by_id(order_id)
        
    if 'error' in result:
        return render_template('order_details.html', error=result['error'])
    
    order = result.get('data')
    
    # Haal abonnementen op voor het e-mailadres
    subscriptions = []
    if order and order.get('billing', {}).get('email'):
        email = order['billing']['email']
        # Gebruik altijd de SQLite functie voor het zoeken naar abonnementen
        # omdat er geen equivalent is in de WooCommerce module
        subscriptions_result = search_subscriptions_by_email(email)
        if 'success' in subscriptions_result or 'data' in subscriptions_result:
            subscriptions = subscriptions_result.get('data', [])
    
    # Haal margegegevens op uit de SQLite database
    margin_data = None
    margin_result = get_order_margin(order_id)
    if 'success' in margin_result:
        margin_data = margin_result.get('data')
    
    return render_template('order_details.html', order=order, subscriptions=subscriptions, margin_data=margin_data)

@app.route('/all')
def all_subscriptions():
    """Toon alle abonnementen met paginering"""
    page = request.args.get('page', 1, type=int)
    limit = 20
    offset = (page - 1) * limit
    
    result = get_all_subscriptions(limit=limit, offset=offset)
    
    if 'error' in result:
        return render_template('index.html', error=result['error'])
    
    subscriptions = result.get('data', [])
    total = result.get('total', 0)
    total_pages = (total + limit - 1) // limit
    
    return render_template('all_subscriptions.html',
                         subscriptions=subscriptions,
                         page=page,
                         total_pages=total_pages,
                         total=total)

@app.route('/all_orders')
def all_orders():
    """Toon alle orders met paginering"""
    page = request.args.get('page', 1, type=int)
    limit = 20
    offset = (page - 1) * limit
    
    # Haal orderstatistieken op
    order_stats = get_monthly_order_stats()
    
    conn = get_db_connection()
    if not conn:
        return render_template('index.html', 
                            error="Kan geen verbinding maken met de database",
                            view_type='orders',
                            order_stats=order_stats)
    
    try:
        # Haal totaal aantal orders op
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM orders")
        total = cursor.fetchone()['total']
        
        # Haal orders op met paginering
        cursor.execute("""
            SELECT o.*, 
                   o.billing_first_name || ' ' || o.billing_last_name as customer_name,
                   GROUP_CONCAT(omd.quantity || 'x ' || omd.base_product, CHAR(10)) as product_list
            FROM orders o
            LEFT JOIN order_margin_data omd ON o.id = omd.order_id
            GROUP BY o.id
            ORDER BY o.date_created DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        orders = []
        for row in cursor.fetchall():
            order_dict = dict(row)
            order_dict['line_items'] = []
            
            if order_dict['product_list']:
                for product in order_dict['product_list'].split('\n'):
                    if product:
                        qty, name = product.split('x ', 1)
                        order_dict['line_items'].append({
                            'quantity': int(qty),
                            'name': name.strip()
                        })
            
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
            
            orders.append(order_dict)
        
        total_pages = (total + limit - 1) // limit
        
        return render_template('index.html',
                             orders=orders,
                             page=page,
                             total_pages=total_pages,
                             total=total,
                             view_type='orders',
                             order_stats=order_stats)
                             
    except Exception as e:
        logger.error(f"Fout bij ophalen orders: {str(e)}")
        return render_template('index.html', 
                            error=f"Fout bij ophalen orders: {str(e)}",
                            view_type='orders',
                            order_stats=order_stats)
    
    finally:
        conn.close()

@app.route('/api/email-suggestions')
def email_suggestions():
    """API endpoint voor e-mail autocomplete suggesties"""
    if not USE_SQLITE:
        return jsonify([])
    
    query = request.args.get('query', '').lower()
    if not query or len(query) < 2:
        return jsonify([])
    
    # Haal alle unieke e-mailadressen op uit de database die beginnen met de query
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'woocommerce.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Zoek naar e-mailadressen die beginnen met de query
        cursor.execute("""
            SELECT DISTINCT billing_email FROM subscriptions 
            WHERE LOWER(billing_email) LIKE ? 
            ORDER BY billing_email
            LIMIT 10
        """, (f"{query}%",))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(results)
    except Exception as e:
        print(f"Fout bij ophalen e-mail suggesties: {str(e)}")
        return jsonify([])

if __name__ == '__main__':
    # Gebruik de standaard poort 5000
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, port=port) 