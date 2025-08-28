#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterator, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta

import pyodbc
import requests
from dotenv import load_dotenv
from dateutil import parser as date_parser

from _woo_client import WooClient

load_dotenv()


@dataclass
class AzureSQLConfig:
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "yes"
    trust_server_certificate: str = "no"


@dataclass
class MontaConfig:
    base_url: str
    username: str
    password: str
    timeout_seconds: float = 60.0


def get_config_from_env() -> AzureSQLConfig:
    try:
        return AzureSQLConfig(
            server=os.environ["AZURE_SQL_SERVER"],
            database=os.environ["AZURE_SQL_DATABASE"],
            username=os.environ["AZURE_SQL_USERNAME"],
            password=os.environ["AZURE_SQL_PASSWORD"],
            driver=os.environ.get("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
            encrypt=os.environ.get("AZURE_SQL_ENCRYPT", "yes"),
            trust_server_certificate=os.environ.get("AZURE_SQL_TRUST_SERVER_CERTIFICATE", "no"),
        )
    except KeyError as exc:
        raise SystemExit(f"Ontbrekende env var: {exc.args[0]}")


def get_woo_config_from_env() -> Tuple[str, str, str]:
    try:
        return (
            os.environ["WOO_BASE_URL"],
            os.environ["WOO_CONSUMER_KEY"],
            os.environ["WOO_CONSUMER_SECRET"],
        )
    except KeyError as exc:
        raise SystemExit(f"Ontbrekende WooCommerce env var: {exc.args[0]}")


def get_monta_config_from_env() -> Optional[MontaConfig]:
    """Haal Monta configuratie op uit environment variables. 
    Retourneert None als Monta configuratie niet beschikbaar is."""
    try:
        return MontaConfig(
            base_url=os.environ["MONTA_BASE_URL"],
            username=os.environ["MONTA_USERNAME"],
            password=os.environ["MONTA_PASSWORD"],
            timeout_seconds=float(os.environ.get("MONTA_TIMEOUT", "60.0")),
        )
    except KeyError:
        logging.warning("Monta configuratie niet gevonden in environment variables. Stock update wordt overgeslagen.")
        return None


def connect_azuresql(cfg: AzureSQLConfig) -> pyodbc.Connection:
    conn_str = (
        f"DRIVER={{{cfg.driver}}};"
        f"SERVER={cfg.server};"
        f"DATABASE={cfg.database};"
        f"UID={cfg.username};"
        f"PWD={cfg.password};"
        f"Encrypt={cfg.encrypt};"
        f"TrustServerCertificate={cfg.trust_server_certificate};"
        f"Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


def is_nullish(value: Optional[str]) -> bool:
    if value is None:
        return True
    v = value.strip()
    return v == "" or v.upper() == "NULL"


def parse_dt(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    try:
        return date_parser.parse(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def to_decimal(value: Optional[str | float | int]) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        try:
            return float(Decimal(str(value)))
        except Exception:
            return 0.0


def normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    return v or None


# ============================================================================
# MONTA STOCK CLIENT
# ============================================================================

class MontaClient:
    def __init__(self, config: MontaConfig):
        self.base_url = config.base_url.rstrip("/")
        self.username = config.username
        self.password = config.password
        self.timeout_seconds = config.timeout_seconds
        self.session = requests.Session()
        
        # Gebruik HTTP Basic Authentication
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Maak een GET request naar de Monta API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Fout bij ophalen van {url}: {e}")
            raise

    def get_stock_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Haal voorraadgegevens op van Monta API"""
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
            
        # Probeer verschillende mogelijke endpoints voor stock data
        stock_endpoints = [
            "api/v2/stock",  # Mogelijk endpoint
            "stock",         # Alternatief endpoint
            "inventory",     # Alternatief endpoint
            "products/stock" # Nog een alternatief
        ]
        
        for endpoint in stock_endpoints:
            try:
                logging.info(f"Proberen Monta endpoint: {endpoint}")
                response = self.get(endpoint, params)
                data = response.json()
                
                # Controleer of we geldige data hebben gekregen
                if isinstance(data, list) and len(data) > 0:
                    logging.info(f"Succesvol stock data ontvangen van endpoint: {endpoint}")
                    return data
                elif isinstance(data, dict) and "data" in data:
                    logging.info(f"Succesvol stock data ontvangen van endpoint: {endpoint}")
                    return data["data"]
                else:
                    logging.warning(f"Geen geldige stock data van endpoint {endpoint}")
                    
            except Exception as e:
                logging.warning(f"Monta endpoint {endpoint} mislukt: {e}")
                continue
        
        # Als alle endpoints falen, probeer een basis product endpoint
        try:
            logging.info("Proberen basis Monta products endpoint voor stock info")
            response = self.get("products", params)
            data = response.json()
            
            if isinstance(data, list):
                # Transformeer product data naar stock format
                stock_data = []
                for product in data:
                    if "sku" in product and "stock_quantity" in product:
                        stock_data.append({
                            "sku": product.get("sku"),
                            "product_name": product.get("name", ""),
                            "stock_quantity": product.get("stock_quantity", 0),
                            "available_quantity": product.get("available_quantity", product.get("stock_quantity", 0)),
                            "reserved_quantity": product.get("reserved_quantity", 0),
                            "location_code": product.get("location_code", ""),
                            "warehouse_code": product.get("warehouse_code", "")
                        })
                return stock_data
                
        except Exception as e:
            logging.error(f"Alle Monta endpoints gefaald. Laatste fout: {e}")
            
        return []


# ============================================================================
# CUSTOMERS UPDATE
# ============================================================================

def update_customers(conn: pyodbc.Connection, woo_client: WooClient) -> None:
    """Update customers tabel - complete replace, inclusief WooCommerce customers en WordPress subscribers"""
    logging.info("Start bijwerken van customers...")
    
    # Tabel legen
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM Customers")
        conn.commit()
        logging.info("Customers tabel geleegd")
    
    customers_data = []
    processed_user_ids = set()  # Om duplicaten te voorkomen
    
    # 1. Alle WooCommerce customers ophalen
    logging.info("Ophalen van WooCommerce customers...")
    woo_customers_count = 0
    for page in woo_client.paginate("customers", per_page=50):
        for customer in page:
            try:
                customer_id = int(customer.get("id"))
                email = normalize_email(customer.get("email"))
                first_name = (customer.get("first_name") or "").strip() or None
                last_name = (customer.get("last_name") or "").strip() or None
                phone = (customer.get("billing", {}).get("phone") or "").strip() or None
                company = (customer.get("billing", {}).get("company") or "").strip() or None
                date_registered = parse_dt(customer.get("date_created"))
                
                if customer_id and email and customer_id not in processed_user_ids:
                    customers_data.append((
                        customer_id, email, first_name, last_name, phone, company, date_registered
                    ))
                    processed_user_ids.add(customer_id)
                    woo_customers_count += 1
            except Exception as e:
                logging.warning(f"Fout bij verwerken WooCommerce customer {customer.get('id')}: {e}")
                continue
    
    logging.info(f"{woo_customers_count} WooCommerce customers gevonden")
    
    # 2. WordPress subscribers ophalen via WooCommerce customers endpoint met role filter
    logging.info("Ophalen van WordPress subscribers...")
    subscribers_count = 0
    try:
        # WooCommerce customers endpoint met role=subscriber parameter gebruiken
        for page in woo_client.paginate("customers", params={"role": "subscriber"}, per_page=50):
            for user in page:
                try:
                    user_id = int(user.get("id"))
                    email = normalize_email(user.get("email"))
                    
                    # Alleen toevoegen als deze user nog niet als WooCommerce customer is toegevoegd
                    if user_id and email and user_id not in processed_user_ids:
                        first_name = (user.get("first_name") or "").strip() or None
                        last_name = (user.get("last_name") or "").strip() or None
                        phone = (user.get("billing", {}).get("phone") or "").strip() or None
                        company = (user.get("billing", {}).get("company") or "").strip() or None
                        date_registered = parse_dt(user.get("date_created"))
                        
                        customers_data.append((
                            user_id, email, first_name, last_name, phone, company, date_registered
                        ))
                        processed_user_ids.add(user_id)
                        subscribers_count += 1
                except Exception as e:
                    logging.warning(f"Fout bij verwerken WordPress subscriber {user.get('id')}: {e}")
                    continue
    except Exception as e:
        logging.warning(f"Fout bij ophalen van WordPress subscribers via customers endpoint: {e}")
        logging.info("Mogelijk ondersteunt de WooCommerce versie geen role filtering op customers endpoint")
    
    logging.info(f"{subscribers_count} WordPress subscribers gevonden")
    
    # Alle customers (WooCommerce + subscribers) invoegen
    if customers_data:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO Customers (CustomerID, Email, FirstName, LastName, Phone, Company, DateRegistered)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                customers_data
            )
            conn.commit()
            logging.info(f"{len(customers_data)} totaal customers ingevoegd ({woo_customers_count} WooCommerce customers + {subscribers_count} subscribers)")
    else:
        logging.warning("Geen customers gevonden")


# ============================================================================
# PRODUCTS UPDATE
# ============================================================================

def update_products(conn: pyodbc.Connection, woo_client: WooClient) -> None:
    """Update products tabel - complete replace"""
    logging.info("Start bijwerken van products...")
    
    # Tabel legen
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM Products")
        conn.commit()
        logging.info("Products tabel geleegd")
    
    # Alle products ophalen vanuit WooCommerce
    products_data = []
    for page in woo_client.paginate("products", per_page=50):
        for product in page:
            try:
                product_id = int(product.get("id"))
                name = (product.get("name") or "").strip()
                status = (product.get("status") or "").strip() or "publish"
                product_type_taxonomy_id = None  # Niet beschikbaar in WooCommerce API
                sku = (product.get("sku") or "").strip() or None
                regular_price = to_decimal(product.get("regular_price")) or 0.0
                sale_price = to_decimal(product.get("sale_price"))
                tax_class = (product.get("tax_class") or "").strip() or None
                created_date = parse_dt(product.get("date_created"))
                modified_date = parse_dt(product.get("date_modified"))
                product_type = (product.get("type") or "").strip() or None
                
                if product_id and name:
                    products_data.append((
                        product_id, name, status, product_type_taxonomy_id, sku,
                        regular_price, sale_price, tax_class, created_date, modified_date, product_type
                    ))
            except Exception as e:
                logging.warning(f"Fout bij verwerken product {product.get('id')}: {e}")
                continue
    
    # Products invoegen
    if products_data:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO Products (ProductID, Name, Status, ProductTypeTaxonomyID, SKU,
                                   RegularPrice, SalePrice, TaxClass, CreatedDate, ModifiedDate, ProductType)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                products_data
            )
            conn.commit()
            logging.info(f"{len(products_data)} products ingevoegd")
    else:
        logging.warning("Geen products gevonden")


# ============================================================================
# STOCK UPDATE
# ============================================================================

def update_stock(conn: pyodbc.Connection, monta_client: Optional[MontaClient], stock_days_back: int = 7) -> None:
    """Update stock tabel vanuit Monta API
    
    Args:
        conn: Database connectie
        monta_client: Monta API client (kan None zijn als niet geconfigureerd)
        stock_days_back: Aantal dagen terug voor stock data (standaard 7)
    """
    if monta_client is None:
        logging.warning("Monta client niet beschikbaar - stock update overgeslagen")
        return
        
    logging.info(f"Start bijwerken van stock (laatste {stock_days_back} dagen)...")
    
    # Datum berekenen
    today = datetime.now()
    start_date = (today - timedelta(days=stock_days_back)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    try:
        # Voorraadgegevens ophalen van Monta
        stock_data = monta_client.get_stock_data(start_date, end_date)
        
        if not stock_data:
            logging.warning("Geen voorraadgegevens ontvangen van Monta API")
            return
        
        # Bestaande records voor deze periode verwijderen
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM Stock WHERE StockDate >= ? AND StockDate <= ?", start_date, end_date)
            deleted_count = cursor.rowcount
            logging.info(f"{deleted_count} bestaande stock records verwijderd voor periode {start_date} tot {end_date}")
            conn.commit()
        
        # Nieuwe records voorbereiden
        insert_data = []
        skipped_count = 0
        
        # Voor elke dag in het bereik de stock data invoegen
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            
            for item in stock_data:
                try:
                    # Extracteer velden met fallbacks
                    sku = (item.get("sku") or item.get("product_sku") or "").strip()
                    if not sku:
                        skipped_count += 1
                        continue
                        
                    product_name = (item.get("product_name") or item.get("name") or "").strip() or None
                    product_id = item.get("product_id") or None
                    if product_id:
                        try:
                            product_id = int(product_id)
                        except (ValueError, TypeError):
                            product_id = None
                    
                    stock_quantity = int(item.get("stock_quantity") or item.get("quantity") or 0)
                    reserved_quantity = int(item.get("reserved_quantity") or item.get("reserved") or 0)
                    available_quantity = int(item.get("available_quantity") or item.get("available") or stock_quantity)
                    
                    location_code = (item.get("location_code") or item.get("location") or "").strip() or None
                    location_name = (item.get("location_name") or "").strip() or None
                    warehouse_code = (item.get("warehouse_code") or item.get("warehouse") or "").strip() or None
                    
                    insert_data.append((
                        sku, product_name, product_id, stock_quantity, reserved_quantity,
                        available_quantity, date_str, location_code, location_name, warehouse_code
                    ))
                    
                except Exception as e:
                    logging.warning(f"Fout bij verwerken stock item {item}: {e}")
                    skipped_count += 1
                    continue
            
            current_date += timedelta(days=1)
        
        # Records invoegen
        if insert_data:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO Stock (
                        ProductSKU, ProductName, ProductID, StockQuantity, ReservedQuantity,
                        AvailableQuantity, StockDate, LocationCode, LocationName, WarehouseCode
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    insert_data
                )
                conn.commit()
                logging.info(f"{len(insert_data)} nieuwe stock records ingevoegd")
                
            if skipped_count > 0:
                logging.warning(f"{skipped_count} stock records overgeslagen wegens ontbrekende SKU of andere fouten")
        else:
            logging.warning("Geen geldige stock records om in te voegen")
            
    except Exception as e:
        logging.error(f"Fout bij bijwerken van stock: {e}")
        raise


# ============================================================================
# SUBSCRIPTIONS UPDATE
# ============================================================================

def update_subscriptions(conn: pyodbc.Connection, woo_client: WooClient) -> None:
    """Update subscriptions tabel - complete replace"""
    logging.info("Start bijwerken van subscriptions...")
    
    # Tabel legen
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM Subscriptions")
        conn.commit()
        logging.info("Subscriptions tabel geleegd")
    
    # Alle subscriptions ophalen vanuit WooCommerce
    subscriptions_data = []
    for page in woo_client.paginate("subscriptions", per_page=50):
        for subscription in page:
            try:
                subscription_id = int(subscription.get("id"))
                status = (subscription.get("status") or "").strip() or "unknown"
                customer_id = int((subscription.get("customer_id") or 0)) or None
                billing_email = None
                try:
                    billing_email = (subscription.get("billing") or {}).get("email") or None
                except Exception:
                    pass
                
                interval = int((subscription.get("billing_interval") or 0)) or 0
                period = (subscription.get("billing_period") or "").strip() or "month"
                
                start_date = parse_dt(subscription.get("date_created_gmt") or subscription.get("start_date_gmt"))
                next_payment = parse_dt(subscription.get("next_payment_date_gmt") or subscription.get("next_payment_gmt"))
                end_date = parse_dt(subscription.get("end_date_gmt") or subscription.get("date_completed_gmt"))
                
                if subscription_id:
                    subscriptions_data.append((
                        subscription_id, status, customer_id, billing_email,
                        interval, period, start_date, next_payment, end_date
                    ))
            except Exception as e:
                logging.warning(f"Fout bij verwerken subscription {subscription.get('id')}: {e}")
                continue
    
    # Subscriptions invoegen
    if subscriptions_data:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO Subscriptions (SubscriptionID, Status, CustomerID, BillingEmail,
                                        BillingInterval, BillingPeriod, StartDate, NextPaymentDate, EndDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                subscriptions_data
            )
            conn.commit()
            logging.info(f"{len(subscriptions_data)} subscriptions ingevoegd")
    else:
        logging.warning("Geen subscriptions gevonden")


# ============================================================================
# SUBSCRIPTION ITEMS UPDATE
# ============================================================================

def update_subscription_items(conn: pyodbc.Connection, woo_client: WooClient) -> None:
    """Update subscription items tabel - complete replace"""
    logging.info("Start bijwerken van subscription items...")
    
    # Tabel legen
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM SubscriptionItems")
        conn.commit()
        logging.info("SubscriptionItems tabel geleegd")
    
    # Alle subscriptions ophalen om items op te halen
    subscription_items_data = []
    
    for page in woo_client.paginate("subscriptions", per_page=50):
        for subscription in page:
            try:
                subscription_id = int(subscription.get("id"))
                line_items = subscription.get("line_items", [])
                
                for item in line_items:
                    try:
                        item_id = int(item.get("id"))
                        name = (item.get("name") or "").strip()
                        product_id = int((item.get("product_id") or 0)) or None
                        variation_id = int((item.get("variation_id") or 0)) or None
                        sku = (item.get("sku") or "").strip() or None
                        quantity = int((item.get("quantity") or 1))
                        
                        subtotal = to_decimal(item.get("subtotal"))
                        subtotal_tax = to_decimal(item.get("subtotal_tax"))
                        total = to_decimal(item.get("total"))
                        total_tax = to_decimal(item.get("total_tax"))
                        tax_class = (item.get("tax_class") or "").strip() or None
                        tax_data = str(item.get("taxes", []))
                        
                        if item_id and subscription_id:
                            subscription_items_data.append((
                                item_id, subscription_id, "line_item", name, product_id, variation_id,
                                sku, quantity, subtotal, subtotal_tax, total, total_tax, tax_class, tax_data
                            ))
                    except Exception as e:
                        logging.warning(f"Fout bij verwerken subscription item {item.get('id')}: {e}")
                        continue
                        
            except Exception as e:
                logging.warning(f"Fout bij verwerken subscription {subscription.get('id')}: {e}")
                continue
    
    # Subscription items invoegen
    if subscription_items_data:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO SubscriptionItems (
                    SubscriptionItemID, SubscriptionID, SubscriptionItemType, SubscriptionItemName,
                    ProductID, VariationID, ProductSKU, Quantity, LineSubtotal, LineSubtotalTax,
                    LineTotal, LineTotalTax, TaxClass, LineTaxData
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                subscription_items_data
            )
            conn.commit()
            logging.info(f"{len(subscription_items_data)} subscription items ingevoegd")
    else:
        logging.warning("Geen subscription items gevonden")


# ============================================================================
# SUBSCRIPTION SHIPPING UPDATE
# ============================================================================

def update_subscription_shipping(conn: pyodbc.Connection, woo_client: WooClient) -> None:
    """Update subscription shipping tabel - complete replace"""
    logging.info("Start bijwerken van subscription shipping...")
    
    # Tabel legen
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM SubscriptionShipping")
        conn.commit()
        logging.info("SubscriptionShipping tabel geleegd")
    
    # Alle subscriptions ophalen om shipping op te halen
    subscription_shipping_data = []
    
    for page in woo_client.paginate("subscriptions", per_page=50):
        for subscription in page:
            try:
                subscription_id = int(subscription.get("id"))
                shipping_lines = subscription.get("shipping_lines", [])
                
                for shipping in shipping_lines:
                    try:
                        shipping_id = int(shipping.get("id"))
                        method_title = (shipping.get("method_title") or "").strip()
                        total = to_decimal(shipping.get("total"))
                        total_tax = to_decimal(shipping.get("total_tax"))
                        
                        if shipping_id and subscription_id:
                            subscription_shipping_data.append((
                                shipping_id, subscription_id, method_title, total, total_tax
                            ))
                    except Exception as e:
                        logging.warning(f"Fout bij verwerken subscription shipping {shipping.get('id')}: {e}")
                        continue
                        
            except Exception as e:
                logging.warning(f"Fout bij verwerken subscription {subscription.get('id')}: {e}")
                continue
    
    # Subscription shipping invoegen
    if subscription_shipping_data:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO SubscriptionShipping (
                    SubscriptionShippingID, SubscriptionID, ShippingMethodName, ShippingCost, ShippingTax
                ) VALUES (?, ?, ?, ?, ?)
                """,
                subscription_shipping_data
            )
            conn.commit()
            logging.info(f"{len(subscription_shipping_data)} subscription shipping records ingevoegd")
    else:
        logging.warning("Geen subscription shipping gevonden")


# ============================================================================
# ORDERS UPDATE (laatste X dagen)
# ============================================================================

def update_orders(conn: pyodbc.Connection, woo_client: WooClient, days_back: int = 30) -> None:
    """Update orders van laatste X dagen (standaard 30 dagen) met batch processing"""
    logging.info(f"Start bijwerken van orders (laatste {days_back} dagen)...")
    
    # Waarschuwing voor grote datasets
    if days_back > 365:
        logging.warning(f"WAARSCHUWING: {days_back} dagen is erg veel data! Dit kan lang duren en veel geheugen gebruiken.")
        logging.warning("Batch processing wordt gebruikt om geheugen problemen te voorkomen.")
    elif days_back > 90:
        logging.info(f"Info: {days_back} dagen is een redelijk grote dataset. Dit kan enkele minuten duren.")
    
    # Datum X dagen geleden in ISO 8601 formaat
    days_ago = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    
    # Batch configuratie
    BATCH_SIZE = 1000  # Aantal orders per batch
    
    # Data containers voor huidige batch
    orders_data = []
    order_items_data = []
    order_shipping_data = []
    
    params = {"after": days_ago, "per_page": 50}
    
    logging.info(f"Start ophalen orders vanaf datum: {days_ago}")
    logging.info(f"Batch verwerking: {BATCH_SIZE} orders per batch")
    
    orders_processed = 0
    page_count = 0
    batch_count = 0
    total_orders_saved = 0
    
    def process_batch(batch_orders, batch_items, batch_shipping, batch_num):
        """Verwerk een batch orders naar de database"""
        nonlocal total_orders_saved, conn
        
        if not batch_orders:
            return 0
            
        logging.info(f"Start verwerken batch {batch_num} met {len(batch_orders)} orders...")
        
        try:
            with conn.cursor() as cursor:
                # Verwijder orders in deze batch (gebaseerd op OrderID)
                order_ids = [order[0] for order in batch_orders if order[0]]
                if order_ids:
                    placeholders = ",".join(["?" for _ in order_ids])
                    cursor.execute(f"DELETE FROM Orders WHERE OrderID IN ({placeholders})", order_ids)
                    deleted_orders = cursor.rowcount
                    logging.info(f"Batch {batch_num}: {deleted_orders} bestaande orders verwijderd")
                
                # Orders invoegen
                cursor.executemany(
                    """
                    INSERT INTO Orders (
                        OrderID, OrderDate, OrderModified, OrderStatus, CustomerID,
                        OrderKey, OrderNumber, Currency, PaymentMethod, OrderTotal,
                        OrderTax, OrderShipping, OrderShippingTax, DateCompleted, DatePaid,
                        BillingFirstName, BillingLastName, BillingEmail, BillingPhone, BillingCompany,
                        BillingAddress1, BillingAddress2, BillingCity, BillingPostcode, BillingCountry,
                        ShippingFirstName, ShippingLastName, ShippingCompany, ShippingAddress1,
                        ShippingAddress2, ShippingCity, ShippingPostcode, ShippingCountry, CreatedVia
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    batch_orders
                )
                logging.info(f"Batch {batch_num}: {len(batch_orders)} orders ingevoegd")
                
                # Order items invoegen
                if batch_items:
                    # Verwijder bestaande order items voor deze orders
                    if order_ids:
                        cursor.execute(f"DELETE FROM OrderItems WHERE OrderID IN ({placeholders})", order_ids)
                        deleted_items = cursor.rowcount
                        logging.info(f"Batch {batch_num}: {deleted_items} bestaande order items verwijderd")
                    
                    cursor.executemany(
                        """
                        INSERT INTO OrderItems (OrderItemID, OrderID, OrderItemType, OrderItemName, ProductID,
                                              VariationID, SKU, Quantity, LineSubtotal, LineSubtotalTax, LineTotal, LineTotalTax, TaxClass)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        batch_items
                    )
                    logging.info(f"Batch {batch_num}: {len(batch_items)} order items ingevoegd")
                
                # Order shipping invoegen
                if batch_shipping:
                    # Verwijder bestaande order shipping voor deze orders
                    if order_ids:
                        cursor.execute(f"DELETE FROM OrderShipping WHERE OrderID IN ({placeholders})", order_ids)
                        deleted_shipping = cursor.rowcount
                        logging.info(f"Batch {batch_num}: {deleted_shipping} bestaande order shipping verwijderd")
                    
                    cursor.executemany(
                        """
                        INSERT INTO OrderShipping (ShippingItemID, OrderID, ShippingMethod, ShippingCost, ShippingTax)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        batch_shipping
                    )
                    logging.info(f"Batch {batch_num}: {len(batch_shipping)} order shipping records ingevoegd")
                
                # Commit deze batch
                conn.commit()
                total_orders_saved += len(batch_orders)
                logging.info(f"Batch {batch_num} succesvol opgeslagen. Totaal verwerkte orders: {total_orders_saved}")
                
        except pyodbc.OperationalError as e:
            if "TCP Provider" in str(e) or "08S01" in str(e):
                logging.warning(f"Database verbinding verloren in batch {batch_num}: {e}")
                logging.info("Poging tot herverbinden...")
                try:
                    # Probeer opnieuw verbinding te maken
                    conn.close()
                    db_config = get_config_from_env()
                    conn = connect_azuresql(db_config)
                    logging.info("Database herverbinding succesvol")
                    # Probeer de batch opnieuw
                    return process_batch(batch_orders, batch_items, batch_shipping, batch_num)
                except Exception as reconnect_error:
                    logging.error(f"Herverbinding mislukt: {reconnect_error}")
                    raise
            else:
                logging.error(f"Database fout bij verwerken van batch {batch_num}: {e}")
                conn.rollback()
                raise
        except Exception as e:
            logging.error(f"Fout bij verwerken van batch {batch_num}: {e}")
            conn.rollback()
            raise
        
        return len(batch_orders)
    
    for page in woo_client.paginate("orders", params):
        page_count += 1
        page_orders = len(page)
        logging.info(f"Verwerken van pagina {page_count} met {page_orders} orders...")
        
        for order in page:
            try:
                order_id = int(order.get("id"))
                order_date = parse_dt(order.get("date_created"))
                order_modified = parse_dt(order.get("date_modified"))
                order_status = (order.get("status") or "").strip() or "unknown"
                customer_id = int((order.get("customer_id") or 0)) or None
                order_key = (order.get("order_key") or "").strip() or None
                order_number = (order.get("number") or "").strip() or None
                currency = (order.get("currency") or "").strip() or "EUR"
                payment_method = (order.get("payment_method") or "").strip() or None
                order_total = to_decimal(order.get("total")) or 0.0
                order_tax = to_decimal(order.get("total_tax")) or 0.0
                order_shipping = to_decimal(order.get("shipping_total")) or 0.0
                order_shipping_tax = to_decimal(order.get("shipping_tax")) or 0.0
                date_completed = parse_dt(order.get("date_completed"))
                date_paid = parse_dt(order.get("date_paid"))
                created_via = (order.get("created_via") or "").strip() or None
                
                # Billing informatie
                billing = order.get("billing", {})
                billing_first_name = (billing.get("first_name") or "").strip() or None
                billing_last_name = (billing.get("last_name") or "").strip() or None
                billing_email = (billing.get("email") or "").strip() or None
                billing_phone = (billing.get("phone") or "").strip() or None
                billing_company = (billing.get("company") or "").strip() or None
                billing_address1 = (billing.get("address_1") or "").strip() or None
                billing_address2 = (billing.get("address_2") or "").strip() or None
                billing_city = (billing.get("city") or "").strip() or None
                billing_postcode = (billing.get("postcode") or "").strip() or None
                billing_country = (billing.get("country") or "").strip() or None
                
                # Shipping informatie
                shipping = order.get("shipping", {})
                shipping_first_name = (shipping.get("first_name") or "").strip() or None
                shipping_last_name = (shipping.get("last_name") or "").strip() or None
                shipping_company = (shipping.get("company") or "").strip() or None
                shipping_address1 = (shipping.get("address_1") or "").strip() or None
                shipping_address2 = (shipping.get("address_2") or "").strip() or None
                shipping_city = (shipping.get("city") or "").strip() or None
                shipping_postcode = (shipping.get("postcode") or "").strip() or None
                shipping_country = (shipping.get("country") or "").strip() or None
                
                if order_id:
                    orders_data.append((
                        order_id, order_date, order_modified, order_status, customer_id,
                        order_key, order_number, currency, payment_method, order_total,
                        order_tax, order_shipping, order_shipping_tax, date_completed,
                        date_paid, billing_first_name, billing_last_name, billing_email,
                        billing_phone, billing_company, billing_address1, billing_address2,
                        billing_city, billing_postcode, billing_country, shipping_first_name,
                        shipping_last_name, shipping_company, shipping_address1,
                        shipping_address2, shipping_city, shipping_postcode, shipping_country,
                        created_via
                    ))
                    orders_processed += 1
                    
                    # Order items ophalen
                    line_items = order.get("line_items", [])
                    for item in line_items:
                        try:
                            # Veilige conversie voor item_id
                            item_id_raw = item.get("id")
                            if not item_id_raw:
                                logging.warning(f"Order item zonder ID gevonden in order {order_id}, skip")
                                continue
                            item_id = int(item_id_raw)
                            
                            product_id = int((item.get("product_id") or 0)) or None
                            variation_id = int((item.get("variation_id") or 0)) or None
                            name = (item.get("name") or "").strip()
                            quantity = int((item.get("quantity") or 1))
                            subtotal = to_decimal(item.get("subtotal"))
                            subtotal_tax = to_decimal(item.get("subtotal_tax"))
                            total = to_decimal(item.get("total"))
                            total_tax = to_decimal(item.get("total_tax"))
                            sku = (item.get("sku") or "").strip() or None
                            
                            if item_id:
                                order_items_data.append((
                                    item_id, order_id, "line_item", name, product_id,
                                    variation_id, sku, quantity, subtotal, subtotal_tax, total, total_tax, None
                                ))
                        except Exception as e:
                            logging.warning(f"Fout bij verwerken order item {item.get('id')}: {e}")
                            continue
                    
                    # Order shipping ophalen
                    shipping_lines = order.get("shipping_lines", [])
                    for shipping in shipping_lines:
                        try:
                            # Veilige conversie voor shipping_id
                            shipping_id_raw = shipping.get("id")
                            if not shipping_id_raw:
                                logging.warning(f"Order shipping zonder ID gevonden in order {order_id}, skip")
                                continue
                            shipping_id = int(shipping_id_raw)
                            
                            method_title = (shipping.get("method_title") or "").strip()
                            method_id = (shipping.get("method_id") or "").strip()
                            total = to_decimal(shipping.get("total"))
                            total_tax = to_decimal(shipping.get("total_tax"))
                            
                            if shipping_id:
                                order_shipping_data.append((
                                    shipping_id, order_id, method_title, total, total_tax
                                ))
                        except Exception as e:
                            logging.warning(f"Fout bij verwerken order shipping {shipping.get('id')}: {e}")
                            continue
                            
            except Exception as e:
                logging.warning(f"Fout bij verwerken order {order.get('id')}: {e}")
                continue
        
        # Voortgang logging per pagina
        logging.info(f"Pagina {page_count} voltooid. Orders verwerkt: {orders_processed} (batch items: {len(orders_data)}, order items: {len(order_items_data)}, shipping: {len(order_shipping_data)})")
        
        # Check of we een batch moeten verwerken
        if len(orders_data) >= BATCH_SIZE:
            batch_count += 1
            process_batch(orders_data, order_items_data, order_shipping_data, batch_count)
            # Reset de data containers voor de volgende batch
            orders_data = []
            order_items_data = []
            order_shipping_data = []
    
    # Verwerk de laatste batch als er nog data over is
    if orders_data:
        batch_count += 1
        process_batch(orders_data, order_items_data, order_shipping_data, batch_count)
    
    # Samenvatting
    logging.info(f"Orders update voltooid!")
    logging.info(f"- Totaal pagina's verwerkt: {page_count}")
    logging.info(f"- Totaal orders opgehaald: {orders_processed}")
    logging.info(f"- Totaal batches verwerkt: {batch_count}")
    logging.info(f"- Totaal orders opgeslagen: {total_orders_saved}")


# ============================================================================
# MAIN UPDATE FUNCTION
# ============================================================================

def update_all(skip_tables: Optional[List[str]] = None, orders_days_back: int = 30, stock_days_back: int = 7) -> None:
    """Update alle tabellen vanuit WooCommerce en Monta in logische volgorde
    
    Args:
        skip_tables: Lijst van tabelnamen om over te slaan (bijv. ['customers', 'products', 'stock'])
        orders_days_back: Aantal dagen terug voor orders (standaard 30)
        stock_days_back: Aantal dagen terug voor stock (standaard 7)
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    if skip_tables is None:
        skip_tables = []
    
    try:
        # Configuratie ophalen
        db_config = get_config_from_env()
        woo_url, woo_key, woo_secret = get_woo_config_from_env()
        monta_config = get_monta_config_from_env()  # Kan None zijn
        
        # Verbindingen maken
        conn = connect_azuresql(db_config)
        woo_client = WooClient(woo_url, woo_key, woo_secret)
        monta_client = MontaClient(monta_config) if monta_config else None
        
        logging.info("Start bijwerken van alle tabellen vanuit WooCommerce en Monta")
        if skip_tables:
            logging.info(f"Overgeslagen tabellen: {', '.join(skip_tables)}")
        
        # Alle beschikbare tabellen met hun update functies
        table_updates = [
            ("customers", lambda conn, woo_client: update_customers(conn, woo_client), "1. Customers (basis tabel)"),
            ("products", lambda conn, woo_client: update_products(conn, woo_client), "2. Products (basis tabel)"),
            ("stock", lambda conn, woo_client: update_stock(conn, monta_client, stock_days_back), "3. Stock van Monta (afhankelijk van products)"),
            ("subscriptions", lambda conn, woo_client: update_subscriptions(conn, woo_client), "4. Subscriptions (afhankelijk van customers)"),
            ("subscription_items", lambda conn, woo_client: update_subscription_items(conn, woo_client), "5. Subscription Items (afhankelijk van subscriptions)"),
            ("subscription_shipping", lambda conn, woo_client: update_subscription_shipping(conn, woo_client), "6. Subscription Shipping (afhankelijk van subscriptions)"),
            ("orders", lambda conn, woo_client: update_orders(conn, woo_client, orders_days_back), "7. Orders, Order Items, Order Shipping (afhankelijk van customers en products)"),
        ]
        
        # Voer updates uit voor niet-overgeslagen tabellen
        for table_name, update_func, description in table_updates:
            if table_name in skip_tables:
                logging.info(f"Overslaan: {description}")
                continue
            
            try:
                logging.info(f"Start: {description}")
                update_func(conn, woo_client)
                logging.info(f"Voltooid: {description}")
            except Exception as e:
                logging.error(f"Fout bij bijwerken van {table_name}: {e}")
                raise
        
        logging.info("Alle geselecteerde tabellen succesvol bijgewerkt!")
        
    except Exception as e:
        logging.error(f"Fout bij bijwerken: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update alle tabellen vanuit WooCommerce en Monta")
    parser.add_argument("--skip", nargs="+", help="Tabellen om over te slaan (bijv. --skip customers products)")
    parser.add_argument("--list-tables", action="store_true", help="Toon alle beschikbare tabellen")
    parser.add_argument("--orders-days", type=int, default=30, help="Aantal dagen terug voor orders (standaard: 30)")
    parser.add_argument("--stock-days", type=int, default=7, help="Aantal dagen terug voor stock (standaard: 7)")
    
    args = parser.parse_args()
    
    if args.list_tables:
        print("Beschikbare tabellen:")
        print("1. customers - Basis tabel met klantgegevens")
        print("2. products - Basis tabel met productgegevens")
        print("3. stock - Voorraadgegevens van Monta")
        print("4. subscriptions - Abonnementen (afhankelijk van customers)")
        print("5. subscription_items - Items binnen abonnementen")
        print("6. subscription_shipping - Verzendgegevens van abonnementen")
        print("7. orders - Bestellingen van laatste X dagen (configureerbaar)")
        print("\nVereiste environment variables:")
        print("WooCommerce: WOO_BASE_URL, WOO_CONSUMER_KEY, WOO_CONSUMER_SECRET")
        print("Azure SQL: AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD")
        print("Monta (optioneel): MONTA_BASE_URL, MONTA_USERNAME, MONTA_PASSWORD")
        print("\nGebruik: python update_all.py --skip customers products --orders-days 60 --stock-days 14")
        sys.exit(0)
    
    skip_tables = args.skip or []
    update_all(skip_tables, args.orders_days, args.stock_days)
 
