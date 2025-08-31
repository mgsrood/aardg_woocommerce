import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import pyodbc
from dataclasses import dataclass


@dataclass
class AzureSQLConfig:
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "yes"
    trust_server_certificate: str = "no"


def get_config_from_env() -> AzureSQLConfig:
    """Haal Azure SQL configuratie op uit environment variabelen."""
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
        raise ValueError(f"Ontbrekende Azure SQL environment variable: {exc.args[0]}")


def connect_azuresql(cfg: AzureSQLConfig) -> pyodbc.Connection:
    """Maak verbinding met Azure SQL Database."""
    conn_str = (
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};"
        f"UID={cfg.username};PWD={cfg.password};"
        f"Encrypt={cfg.encrypt};TrustServerCertificate={cfg.trust_server_certificate};"
        f"Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


def extract_webhook_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extraheer relevante data uit webhook payload."""
    if not payload:
        return {}
    
    # Billing informatie
    billing = payload.get('billing', {})
    billing_email = billing.get('email') if billing else None
    billing_first_name = billing.get('first_name') if billing else None
    billing_last_name = billing.get('last_name') if billing else None
    
    # Customer ID - voor customer.created webhooks
    customer_id = payload.get('id') if payload.get('id') else None
    
    # Order/Subscription ID - alleen voor order-gerelateerde webhooks
    order_id = None
    subscription_id = None
    
    # Bepaal of het een order/subscription is door te kijken naar order-specifieke velden
    if payload.get('line_items') or payload.get('total') or payload.get('currency'):
        # Dit is een order, gebruik id als order_id
        order_id = payload.get('id')
        # Bepaal of het een subscription is
        if payload.get('billing_period') or payload.get('next_payment_date'):
            subscription_id = order_id
            order_id = None
        # Als het een order is, reset customer_id
        customer_id = None
    
    # Product informatie
    line_items = payload.get('line_items', [])
    product_ids = []
    product_names = []
    
    for item in line_items:
        if item.get('product_id'):
            product_ids.append(item['product_id'])
        if item.get('name'):
            product_names.append(item['name'])
    
    # Order totaal en currency
    order_total = None
    try:
        if payload.get('total'):
            order_total = float(payload['total'])
    except (ValueError, TypeError):
        pass
    
    currency = payload.get('currency')
    payment_method = payload.get('payment_method_title') or payload.get('payment_method')
    
    return {
        'billing_email': billing_email,
        'billing_first_name': billing_first_name,
        'billing_last_name': billing_last_name,
        'customer_id': customer_id,
        'order_id': order_id,
        'subscription_id': subscription_id,
        'product_ids': json.dumps(product_ids) if product_ids else None,
        'product_names': json.dumps(product_names) if product_names else None,
        'order_total': order_total,
        'currency': currency,
        'payment_method': payment_method
    }


def log_to_azure_sql(
    route: str,
    source: str,
    script_name: str,
    status: str,
    message: str,
    processing_time_ms: Optional[int] = None,
    request_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    error_details: Optional[Dict[str, Any]] = None,
    retry_count: int = 0
) -> None:
    """
    Log webhook verwerking naar Azure SQL Database.
    
    Args:
        route: De webhook route (bijv. '/woocommerce/add_ac_product_tag')
        source: De bron van de webhook (bijv. 'WooCommerce', 'Active Campaign')
        script_name: Naam van het script/functie
        status: Status van de verwerking ('success', 'error', 'warning')
        message: Beschrijving van het resultaat
        processing_time_ms: Verwerkingstijd in milliseconden
        request_id: Unieke request ID
        payload: De webhook payload data
        error_details: Extra error informatie
        retry_count: Aantal retry pogingen
    """
    try:
        # Check of Azure SQL logging uitgeschakeld is
        if os.getenv('SKIP_AZURE_SQL_LOGGING', '').lower() in ['true', '1', 'yes']:
            logging.info("Azure SQL logging overgeslagen (SKIP_AZURE_SQL_LOGGING=true)")
            return
        
        # Haal configuratie op
        try:
            cfg = get_config_from_env()
        except ValueError as e:
            logging.warning(f"Azure SQL configuratie ontbreekt: {e}")
            return
        
        # Extraheer webhook data
        webhook_data = extract_webhook_data(payload) if payload else {}
        
        # Bereid error details voor
        error_type = None
        error_details_json = None
        if error_details:
            error_type = error_details.get('type')
            error_details_json = json.dumps(error_details)
        
        # Environment
        environment = os.getenv('ENVIRONMENT', 'development')
        
        # Maak verbinding en insert log
        with connect_azuresql(cfg) as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO [dbo].[WebhookLogs] (
                    [Route], [Source], [ScriptName], [Status], [Message],
                    [ProcessingTimeMs], [RequestID], [RetryCount],
                    [BillingEmail], [BillingFirstName], [BillingLastName],
                    [CustomerID], [OrderID], [SubscriptionID], [ProductIDs], [ProductNames],
                    [OrderTotal], [Currency], [PaymentMethod],
                    [ErrorType], [ErrorDetails], [Environment]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    route,
                    source,
                    script_name,
                    status,
                    message,
                    processing_time_ms,
                    request_id,
                    retry_count,
                    webhook_data.get('billing_email'),
                    webhook_data.get('billing_first_name'),
                    webhook_data.get('billing_last_name'),
                    webhook_data.get('customer_id'),
                    webhook_data.get('order_id'),
                    webhook_data.get('subscription_id'),
                    webhook_data.get('product_ids'),
                    webhook_data.get('product_names'),
                    webhook_data.get('order_total'),
                    webhook_data.get('currency'),
                    webhook_data.get('payment_method'),
                    error_type,
                    error_details_json,
                    environment
                ))
                conn.commit()
        
        logging.debug(f"Webhook log geschreven naar Azure SQL voor route {route}")
        
    except Exception as e:
        logging.error(f"Fout bij loggen naar Azure SQL: {str(e)}")
