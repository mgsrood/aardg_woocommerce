from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_caching import Cache
from utils.woocommerce import search_subscriptions_by_id as wc_search_by_id, get_order_by_id as wc_get_order_by_id
from utils.woocommerce import get_subscription_statistics as wc_get_subscription_statistics, get_subscription_products
from utils.sqlite_db import search_subscriptions_by_id as db_search_by_id
from utils.sqlite_db import search_subscriptions_by_email, get_all_subscriptions, get_orders_by_email, search_subscriptions_by_name
from utils.sqlite_db import get_order_by_id as db_get_order_by_id, search_orders_by_name, get_subscription_statistics
from utils.sqlite_db import init_db
from utils.bigquery_import import get_order_margin
import os
import sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import json
from concurrent.futures import ThreadPoolExecutor
from utils.woocommerce import (
    update_subscription_status,
    update_subscription_billing_interval,
    update_subscription_next_payment_date,
    update_subscription_shipping_address,
    update_subscription_billing_address,
    update_subscription_expiry_date,
    get_subscription_products,
    wcapi
)
from utils.monta_api import MontaAPI
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User

# Configureer logging
logger = logging.getLogger(__name__)

# Laad environment variables
load_dotenv()

app = Flask(__name__)
app.config.from_object('config.Config')  # Zorg dat we de Config class gebruiken

# Initialiseer de database
init_db()

# Configureer caching
cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300  # 5 minuten
})

# Bepaal welke databron te gebruiken
USE_SQLITE = os.getenv('USE_SQLITE', 'true').lower() == 'true'

# Na het maken van de Flask app
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Log in om toegang te krijgen tot deze pagina.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    try:
        # Pad naar de database
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')
        
        # Verbinding maken met de database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Gebruiker ophalen
        cursor.execute('SELECT id, username, password_hash FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        # Verbinding sluiten
        conn.close()
        
        # Als gebruiker gevonden is, maak een User object
        if user_data:
            return User(
                id=user_data[0],
                username=user_data[1],
                password_hash=user_data[2]
            )
    except Exception as e:
        print(f"Database error in load_user: {e}")
    
    # Fallback naar hardgecodeerde gebruiker
    if user_id == '1':  # Admin user
        return User(1, 'admin', 'dummy_hash')  # Het echte hash zit in get_user_by_username
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.get_user_by_username(username)
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            flash('Je bent succesvol ingelogd!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Ongeldige gebruikersnaam of wachtwoord', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Je bent uitgelogd', 'info')
    return redirect(url_for('login'))

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
                   o.line_items as product_list
            FROM orders o
            ORDER BY o.created_date DESC 
            LIMIT ?
        """, (limit,))
        
        orders = []
        for row in cursor.fetchall():
            order_dict = dict(row)
            
            # Parse line_items JSON
            if order_dict.get('line_items'):
                try:
                    line_items = json.loads(order_dict['line_items'])
                    order_dict['line_items'] = []
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
                    order_dict['line_items'] = []
            else:
                order_dict['line_items'] = []
            
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
            WHERE created_date >= ? AND created_date < ?
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
@login_required
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
@login_required
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
        # Valideer order_id formaat
        if not order_id.isdigit():
            return render_template('index.html', 
                                error="Order ID moet een geldig nummer zijn.",
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
        
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
            
        except Exception as e:
            logger.error(f"Fout bij zoeken order op ID {order_id}: {str(e)}")
            return render_template('index.html', 
                                error="Er is een fout opgetreden bij het zoeken van de order.",
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
        if not name.strip():
            return render_template('index.html', 
                                error="Voer een geldige naam in om te zoeken.",
                                view_type='orders',
                                order_stats=order_stats,
                                recent_orders=recent_orders)
        
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
    try:
        # Haal subscription en orders parallel op
        with ThreadPoolExecutor() as executor:
            # Haal subscription op
            subscription_future = executor.submit(wc_search_by_id, subscription_id)
            subscription_result = subscription_future.result()
            
            # Haal subscription uit het resultaat
            subscription = subscription_result.get('data', [])[0] if subscription_result.get('data') else None
            
            # Als er een fout is, geef deze door samen met subscription
            if 'error' in subscription_result:
                return render_template('subscription_details.html', 
                                    error=subscription_result['error'],
                                    subscription=subscription,
                                    today=date.today().isoformat())
            
            # Haal orders op voor het e-mailadres als die er is
            orders = []
            if subscription and subscription.get('billing', {}).get('email'):
                email = subscription['billing']['email']
                logger.info(f"Zoeken naar orders voor e-mailadres: {email}")
                
                if USE_SQLITE:
                    orders_future = executor.submit(get_orders_by_email, email)
                    orders_result = orders_future.result()
                    logger.info(f"SQLite orders resultaat: {orders_result}")
                    if 'success' in orders_result:
                        orders = orders_result.get('data', [])
                        logger.info(f"Aantal orders gevonden: {len(orders)}")
                else:
                    # Fallback naar WooCommerce API als SQLite niet wordt gebruikt
                    from utils.woocommerce import get_orders_by_email as wc_get_orders_by_email
                    orders_future = executor.submit(wc_get_orders_by_email, email)
                    orders_result = orders_future.result()
                    logger.info(f"WooCommerce orders resultaat: {orders_result}")
                    if 'success' in orders_result:
                        orders = orders_result.get('data', [])
                        logger.info(f"Aantal orders gevonden: {len(orders)}")
            
            # Voeg huidige datum toe voor datumvalidatie
            today = date.today().isoformat()
            
            return render_template('subscription_details.html', 
                                subscription=subscription, 
                                orders=orders, 
                                use_woocommerce=True,
                                today=today)
                                
    except Exception as e:
        logger.error(f"Fout bij ophalen subscription details: {str(e)}")
        return render_template('subscription_details.html', 
                            error=f"Er is een fout opgetreden: {str(e)}",
                            subscription=None,
                            today=date.today().isoformat())

@app.route('/order/<int:order_id>')
@login_required
def order_details(order_id):
    """Toon details van een specifieke order"""
    try:
        # Probeer eerst de WooCommerce API met een langere timeout
        wcapi.timeout = 60  # Verhoog timeout naar 60 seconden
        result = wc_get_order_by_id(order_id)
        
        if 'error' in result:
            # Als er een fout is met de WooCommerce API, probeer SQLite
            if USE_SQLITE:
                logger.info(f"Fallback naar SQLite voor order {order_id}")
                result = db_get_order_by_id(order_id)
                if 'error' in result:
                    return render_template('order_details.html', error=result['error'])
                order = result.get('data')
            else:
                return render_template('order_details.html', error=result['error'])
        else:
            order = result.get('data')
        
        # Haal abonnementen op voor het e-mailadres
        subscriptions = []
        if order and order.get('billing', {}).get('email'):
            email = order['billing']['email']
            # Gebruik altijd de SQLite functie voor het zoeken naar abonnementen
            subscriptions_result = search_subscriptions_by_email(email)
            if 'success' in subscriptions_result or 'data' in subscriptions_result:
                subscriptions = subscriptions_result.get('data', [])
        
        # Haal margegegevens op uit de SQLite database
        margin_data = None
        margin_result = get_order_margin(order_id)
        if 'success' in margin_result:
            margin_data = margin_result.get('data')
        
        return render_template('order_details.html', order=order, subscriptions=subscriptions, margin_data=margin_data)
        
    except Exception as e:
        logger.error(f"Onverwachte fout bij ophalen order {order_id}: {str(e)}")
        return render_template('order_details.html', error=f"Er is een fout opgetreden bij het ophalen van de order: {str(e)}")

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
                   o.line_items as product_list
            FROM orders o
            ORDER BY o.created_date DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
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

@app.route('/subscription/<int:subscription_id>/update_status', methods=['POST'])
def update_subscription_status_route(subscription_id):
    """Update de status van een abonnement"""
    try:
        new_status = request.json.get('status')
        if not new_status:
            return jsonify({"error": "Geen status opgegeven"}), 400
            
        result = update_subscription_status(subscription_id, new_status)
        
        if 'error' in result:
            return jsonify(result), result.get('status', 500)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/<int:subscription_id>/update_interval', methods=['POST'])
def update_subscription_interval_route(subscription_id):
    """Update de factureringsinterval van een abonnement"""
    try:
        billing_interval = request.json.get('billing_interval')
        billing_period = request.json.get('billing_period', 'week')
        
        if not billing_interval:
            return jsonify({"error": "Geen interval opgegeven"}), 400
            
        result = update_subscription_billing_interval(subscription_id, billing_interval, billing_period)
        
        if 'error' in result:
            return jsonify(result), result.get('status', 500)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/<int:subscription_id>/update_next_payment', methods=['POST'])
def update_subscription_next_payment_route(subscription_id):
    """Update de volgende betaaldatum van een abonnement"""
    try:
        next_payment_date = request.json.get('next_payment_date')
        next_payment_time = request.json.get('next_payment_time')
        
        if not next_payment_date:
            return jsonify({"error": "Geen datum opgegeven"}), 400
            
        result = update_subscription_next_payment_date(
            subscription_id, 
            next_payment_date,
            next_payment_time
        )
        
        if 'error' in result:
            return jsonify(result), result.get('status', 500)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/<int:subscription_id>/update_shipping', methods=['POST'])
def update_subscription_shipping_route(subscription_id):
    """Update het verzendadres van een abonnement"""
    try:
        shipping_address = request.json.get('shipping_address')
        
        if not shipping_address:
            return jsonify({"error": "Geen adres opgegeven"}), 400
            
        result = update_subscription_shipping_address(subscription_id, shipping_address)
        
        if 'error' in result:
            return jsonify(result), result.get('status', 500)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/<int:subscription_id>/update_billing', methods=['POST'])
def update_subscription_billing_route(subscription_id):
    """Update het factuuradres van een abonnement"""
    try:
        billing_address = request.json.get('billing_address')
        
        if not billing_address:
            return jsonify({"error": "Geen adres opgegeven"}), 400
            
        result = update_subscription_billing_address(subscription_id, billing_address)
        
        if 'error' in result:
            return jsonify(result), result.get('status', 500)
            
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/available_products', methods=['GET'])
def get_available_subscription_products():
    """
    Endpoint om beschikbare abonnementsproducten op te halen
    """
    try:
        print("Ophalen van beschikbare abonnementsproducten")
        result = get_subscription_products()
        
        if result.get("error"):
            print(f"Fout bij ophalen producten: {result.get('error')}")
            return jsonify(result), result.get("status", 500)
            
        print(f"Succesvol {len(result.get('data', []))} producten opgehaald")
        return jsonify(result)
    except Exception as e:
        error_message = f"Onverwachte fout bij ophalen beschikbare producten: {str(e)}"
        print(error_message)
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return jsonify({"error": error_message, "status": 500}), 500

@app.route('/subscription/<int:subscription_id>/update_products', methods=['POST'])
def update_subscription_products(subscription_id):
    """Update de producten en verzendkosten van een abonnement"""
    try:
        products = request.json.get('products')
        shipping_lines = request.json.get('shipping_lines', [])
        
        print(f"Ontvangen producten: {products}")
        print(f"Ontvangen verzendkosten: {shipping_lines}")
        
        if not products:
            return jsonify({"error": "Geen producten opgegeven"}), 400
            
        # Haal het huidige abonnement op
        current_subscription = wcapi.get(f"subscriptions/{subscription_id}")
        if current_subscription.status_code != 200:
            return jsonify({"error": "Kon het abonnement niet ophalen"}), 500
            
        # Haal de huidige data op
        current_data = current_subscription.json()
        print(f"Huidige abonnementsdata: {current_data}")
        print(f"Huidige verzendkosten: {current_data.get('shipping_lines', [])}")
        
        # Maak een nieuwe data structuur met de bestaande line_items
        data = {
            'line_items': [],
            'shipping_lines': [],
            'status': current_data.get('status', 'active')
        }
        
        # Verwerk alle bestaande producten
        for existing_item in current_data.get('line_items', []):
            product_id = existing_item.get('product_id')
            
            # Zoek of dit product in de nieuwe lijst staat
            new_product = None
            for product in products:
                if product['product_id'] == product_id:
                    new_product = product
                    break
            
            if new_product:
                # Update het product met de nieuwe hoeveelheid
                data['line_items'].append({
                    'id': existing_item['id'],
                    'product_id': product_id,
                    'quantity': new_product['quantity'],
                    'subtotal': str(float(new_product['price']) * float(new_product['quantity'])),
                    'total': str(float(new_product['price']) * float(new_product['quantity']))
                })
            else:
                # Zet de hoeveelheid op 0 voor producten die niet meer in de lijst staan
                data['line_items'].append({
                    'id': existing_item['id'],
                    'product_id': product_id,
                    'quantity': 0,
                    'subtotal': '0.00',
                    'total': '0.00'
                })
        
        # Voeg eventuele nieuwe producten toe
        for new_product in products:
            product_id = new_product['product_id']
            
            # Controleer of dit product al bestaat
            exists = False
            for item in data['line_items']:
                if item.get('product_id') == product_id:
                    exists = True
                    break
            
            if not exists:
                # Voeg het nieuwe product toe
                data['line_items'].append({
                    'product_id': product_id,
                    'quantity': new_product['quantity'],
                    'subtotal': str(float(new_product['price']) * float(new_product['quantity'])),
                    'total': str(float(new_product['price']) * float(new_product['quantity']))
                })
        
        # Verwerk de verzendkosten
        if shipping_lines:
            print("Nieuwe verzendkosten ontvangen, deze worden toegepast:")
            for shipping in shipping_lines:
                print(f"Verzendkost: {shipping}")
                if shipping.get('method_id'):
                    shipping_line = {
                        'method_id': shipping['method_id'],
                        'method_title': shipping['method_title'],
                        'total': str(shipping['total'])
                    }
                    print(f"Toegevoegde verzendkost: {shipping_line}")
                    data['shipping_lines'].append(shipping_line)
        else:
            print("Geen nieuwe verzendkosten ontvangen, bestaande worden behouden:")
            for shipping in current_data.get('shipping_lines', []):
                if shipping.get('method_id'):
                    print(f"Bestaande verzendkost: {shipping}")
                    data['shipping_lines'].append({
                        'id': shipping.get('id'),
                        'method_id': shipping['method_id'],
                        'method_title': shipping['method_title'],
                        'total': str(shipping['total'])
                    })
        
        print(f"Data die naar WooCommerce wordt gestuurd: {data}")
        
        # Update het abonnement met de nieuwe data
        response = wcapi.put(f"subscriptions/{subscription_id}", data)
        
        print(f"WooCommerce response status: {response.status_code}")
        print(f"WooCommerce response body: {response.text}")
        
        if response.status_code != 200:
            return jsonify({"error": f"Fout bij updaten abonnement: {response.text}"}), response.status_code
            
        # Haal het bijgewerkte abonnement op om te controleren
        updated_subscription = wcapi.get(f"subscriptions/{subscription_id}")
        print(f"Bijgewerkte abonnementsdata: {updated_subscription.json()}")
        print(f"Bijgewerkte verzendkosten: {updated_subscription.json().get('shipping_lines', [])}")
        
        return jsonify({"success": True, "data": response.json()})
        
    except Exception as e:
        print(f"Exception: {str(e)}")
        import traceback
        print(f"Stacktrace: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

def sync_products_to_sqlite():
    """Synchroniseer producten met SQLite database"""
    try:
        # Haal alle producten op van WooCommerce
        response = wcapi.get("products", params={'per_page': 100})
        if response.status_code != 200:
            logger.error(f"Fout bij ophalen producten: {response.text}")
            return False
            
        products = response.json()
        
        # Maak database connectie
        conn = get_db_connection()
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Maak products tabel als deze niet bestaat
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    sku TEXT,
                    price REAL,
                    regular_price REAL,
                    sale_price REAL,
                    status TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Update of voeg producten toe
            for product in products:
                cursor.execute("""
                    INSERT OR REPLACE INTO products 
                    (id, name, sku, price, regular_price, sale_price, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    product['id'],
                    product['name'],
                    product.get('sku', ''),
                    float(product.get('price', 0)),
                    float(product.get('regular_price', 0)),
                    float(product.get('sale_price', 0)),
                    product.get('status', '')
                ))
            
            conn.commit()
            return True
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Fout bij synchroniseren producten: {str(e)}")
        return False

def search_products(query):
    """Zoek producten in SQLite database"""
    try:
        conn = get_db_connection()
        if not conn:
            return {"error": "Kan geen verbinding maken met de database"}
            
        cursor = conn.cursor()
        
        # Zoek op naam of SKU
        cursor.execute("""
            SELECT id, name, sku, price, regular_price, sale_price, status
            FROM products
            WHERE LOWER(name) LIKE ? OR LOWER(sku) LIKE ?
            ORDER BY name
            LIMIT 50
        """, (f"%{query.lower()}%", f"%{query.lower()}%"))
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row['id'],
                'name': row['name'],
                'sku': row['sku'],
                'price': row['price'],
                'regular_price': row['regular_price'],
                'sale_price': row['sale_price'],
                'status': row['status']
            })
            
        return {"success": True, "data": products}
        
    except Exception as e:
        logger.error(f"Fout bij zoeken producten: {str(e)}")
        return {"error": str(e)}
    finally:
        conn.close()

@app.route('/api/search-products')
def api_search_products():
    """API endpoint voor product zoeken"""
    query = request.args.get('query', '')
    if not query or len(query) < 2:
        return jsonify([])
        
    result = search_products(query)
    if 'error' in result:
        return jsonify({"error": result['error']}), 500
        
    return jsonify(result['data'])

@app.route('/subscription/<int:subscription_id>/orders')
@cache.memoize(timeout=300)  # Cache voor 5 minuten
def get_subscription_orders(subscription_id):
    """API endpoint voor het ophalen van orders voor een abonnement"""
    try:
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Geen e-mailadres opgegeven"}), 400
            
        if USE_SQLITE:
            result = get_orders_by_email(email)
        else:
            # Fallback naar WooCommerce API als SQLite niet wordt gebruikt
            from utils.woocommerce import get_orders_by_email as wc_get_orders_by_email
            result = wc_get_orders_by_email(email)
            
        if 'error' in result:
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Fout bij ophalen orders: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/<int:subscription_id>/update_addresses', methods=['POST'])
def update_subscription_addresses_route(subscription_id):
    """Update zowel factuur- als verzendadres van een abonnement"""
    try:
        data = request.json
        print(f"Ontvangen data: {data}")
        
        billing_address = data.get('billing')
        shipping_address = data.get('shipping')
        
        print(f"Billing address: {billing_address}")
        print(f"Shipping address: {shipping_address}")
        
        if not billing_address or not shipping_address:
            return jsonify({"error": "Zowel factuur- als verzendadres zijn verplicht"}), 400
        
        # Update factuuradres
        billing_result = update_subscription_billing_address(subscription_id, billing_address)
        print(f"Billing result: {billing_result}")
        if 'error' in billing_result:
            return jsonify(billing_result), billing_result.get('status', 500)
        
        # Update verzendadres
        shipping_result = update_subscription_shipping_address(subscription_id, shipping_address)
        print(f"Shipping result: {shipping_result}")
        if 'error' in shipping_result:
            return jsonify(shipping_result), shipping_result.get('status', 500)
        
        return jsonify({"success": True, "data": shipping_result.get('data')})
        
    except Exception as e:
        print(f"Error in update_addresses: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/subscription/<int:subscription_id>/update_expiry_date', methods=['POST'])
def update_subscription_expiry_date_route(subscription_id):
    """Update de vervaldatum van een abonnement"""
    try:
        # Haal de nieuwe vervaldatum op uit het formulier
        expiry_date = request.form.get('expiry_date')
        expiry_time = request.form.get('expiry_time', '00:00')
        
        # Valideer de datum
        if not expiry_date:
            return jsonify({"success": False, "error": "Geen vervaldatum opgegeven"})
        
        # Update de vervaldatum
        from utils.woocommerce import update_subscription_expiry_date
        result = update_subscription_expiry_date(subscription_id, expiry_date, expiry_time)
        
        if 'error' in result:
            return jsonify({"success": False, "error": result['error']})
        
        return jsonify({"success": True, "message": "Vervaldatum succesvol bijgewerkt"})
        
    except Exception as e:
        logger.error(f"Fout bij updaten vervaldatum: {str(e)}")
        return jsonify({"success": False, "error": f"Er is een fout opgetreden: {str(e)}"})

# Voeg de adjust_time filter toe
@app.template_filter('adjust_time')
def adjust_time(time_str):
    if not time_str:
        return '00:00'
    try:
        hours, minutes = map(int, time_str.split(':'))
        adjusted_hours = (hours + 1) % 24
        return f"{adjusted_hours:02d}:{minutes:02d}"
    except:
        return time_str

@app.route('/order/<int:order_id>/forward_to_monta', methods=['POST'])
def forward_order_to_monta(order_id):
    """Stuur een order door naar het distributiecentrum"""
    try:
        # Haal verzendmoment op uit request
        data = request.get_json()
        if not data or 'shipment_date' not in data:
            return jsonify({"error": "Geen verzenddatum opgegeven"}), 400
            
        shipment_date = data['shipment_date']
        
        # Haal order op via WooCommerce API
        wcapi.timeout = 60  # Verhoog timeout voor betrouwbaarheid
        result = wcapi.get(f"orders/{order_id}")
        
        if result.status_code != 200:
            return jsonify({"error": f"Order niet gevonden: {result.text}"}), 404
            
        order = result.json()
        
        # Controleer order status
        if order['status'] not in ['pending', 'on-hold']:
            return jsonify({
                "error": f"Order kan niet worden doorgestuurd. Status moet 'In afwachting' of 'On-hold' zijn, maar is: {order['status']}"
            }), 400
            
        # Controleer of order al is doorgestuurd
        if order.get('meta_data'):
            for meta in order['meta_data']:
                if meta.get('key') == '_monta_order_id' and meta.get('value'):
                    return jsonify({"error": "Order is al doorgestuurd naar het distributiecentrum"}), 400
            
        # Maak Monta order data
        monta_data = {
            "InternalWebshopOrderId": str(order['id']),
            "WebshopOrderId": str(order['id']),
            "Reference": str(order['id']),
            "Origin": "WooCommerce",
            "ConsumerDetails": {
                "DeliveryAddress": {
                    "FirstName": order['shipping']['first_name'],
                    "LastName": order['shipping']['last_name'],
                    "Street": order['shipping']['address_1'].split()[0],
                    "HouseNumber": order['shipping']['address_1'].split()[1] if len(order['shipping']['address_1'].split()) > 1 else "",
                    "HouseNumberAddition": order['shipping']['address_2'] or "",
                    "PostalCode": order['shipping']['postcode'],
                    "City": order['shipping']['city'],
                    "CountryCode": order['shipping']['country']
                },
                "InvoiceAddress": {
                    "FirstName": order['billing']['first_name'],
                    "LastName": order['billing']['last_name'],
                    "Street": order['billing']['address_1'].split()[0],
                    "HouseNumber": order['billing']['address_1'].split()[1] if len(order['billing']['address_1'].split()) > 1 else "",
                    "HouseNumberAddition": order['billing']['address_2'] or "",
                    "PostalCode": order['billing']['postcode'],
                    "City": order['billing']['city'],
                    "CountryCode": order['billing']['country']
                },
                "B2B": bool(order['billing'].get('company')),
                "CommunicationLanguageCode": "NL"
            },
            "PlannedShipmentDate": f"{shipment_date}T00:00:00.000Z",
            "ShipOnPlannedShipmentDate": True,
            "Blocked": True,
            "Lines": []
        }
        
        # Voeg producten toe
        for item in order.get('line_items', []):
            monta_data['Lines'].append({
                "Sku": item.get('sku', ''),
                "OrderedQuantity": item['quantity'],
                "Description": item['name']
            })
            
        # Stuur order door naar Monta
        monta_api = MontaAPI()
        result = monta_api.create_order(monta_data)
        
        if 'error' in result:
            return jsonify({"error": f"Fout bij aanmaken order in distributiecentrum: {result['error']}"}), 500
            
        # Update WooCommerce met Monta order ID en status
        update_data = {
            'meta_data': [
                {
                    'key': '_monta_order_id',
                    'value': result['id']
                },
                {
                    'key': '_monta_order_status',
                    'value': 'blocked'
                },
                {
                    'key': '_monta_shipment_date',
                    'value': shipment_date
                }
            ]
        }
        
        # Update de order in WooCommerce
        update_result = wcapi.put(f"orders/{order_id}", update_data)
        
        if update_result.status_code != 200:
            logger.error(f"Fout bij updaten WooCommerce order met Monta gegevens: {update_result.text}")
            
        return jsonify({
            "success": True,
            "message": "Order is succesvol doorgestuurd naar het distributiecentrum",
            "monta_order_id": result['id']
        })
        
    except Exception as e:
        logger.error(f"Onverwachte fout bij doorsturen order: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Gebruik de standaard poort 5000
    port = int(os.getenv('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
    sync_products_to_sqlite()  # Synchroniseer producten bij opstarten 