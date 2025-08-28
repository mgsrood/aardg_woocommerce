#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import pyodbc
from dotenv import load_dotenv

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


def get_woo_config_from_env() -> Tuple[str, str, str]:
    try:
        return (
            os.environ["WOO_BASE_URL"],
            os.environ["WOO_CONSUMER_KEY"],
            os.environ["WOO_CONSUMER_SECRET"],
        )
    except KeyError as exc:
        raise SystemExit(f"Ontbrekende WooCommerce env var: {exc.args[0]}")


def get_existing_subscription_items(conn: pyodbc.Connection) -> Dict[int, Dict[str, Any]]:
    """Haal bestaande subscription_items op uit de database"""
    query = """
    SELECT SubscriptionItemID, SubscriptionID, SubscriptionItemType, SubscriptionItemName,
           ProductID, VariationID, ProductSKU, Quantity, LineSubtotal, LineSubtotalTax,
           LineTotal, LineTotalTax, TaxClass, LineTaxData
    FROM SubscriptionItems
    """
    
    existing_items = {}
    with conn.cursor() as cursor:
        cursor.execute(query)
        for row in cursor.fetchall():
            item_id = row[0]
            existing_items[item_id] = {
                'SubscriptionItemID': row[0],
                'SubscriptionID': row[1],
                'SubscriptionItemType': row[2],
                'SubscriptionItemName': row[3],
                'ProductID': row[4],
                'VariationID': row[5],
                'ProductSKU': row[6],
                'Quantity': row[7],
                'LineSubtotal': row[8],
                'LineSubtotalTax': row[9],
                'LineTotal': row[10],
                'LineTotalTax': row[11],
                'TaxClass': row[12],
                'LineTaxData': row[13]
            }
    
    logging.info(f"Bestaande {len(existing_items)} subscription_items opgehaald")
    return existing_items


def get_subscription_items_from_woo(woo_client: WooClient, subscription_id: int) -> List[Dict[str, Any]]:
    """Haal subscription items op voor een specifieke subscription vanuit WooCommerce"""
    try:
        # Haal subscription op
        subscription = woo_client.get(f"subscriptions/{subscription_id}")
        if not subscription:
            return []
        
        # Haal line items op uit de subscription
        line_items = subscription.get("line_items", [])
        
        items = []
        for item in line_items:
            subscription_item = {
                'SubscriptionItemID': item.get("id"),
                'SubscriptionID': subscription_id,
                'SubscriptionItemType': 'line_item',
                'SubscriptionItemName': item.get("name", ""),
                'ProductID': item.get("product_id"),
                'VariationID': item.get("variation_id") or 0,
                'ProductSKU': item.get("sku"),
                'Quantity': item.get("quantity", 1),
                'LineSubtotal': float(item.get("subtotal", 0)),
                'LineSubtotalTax': float(item.get("subtotal_tax", 0)),
                'LineTotal': float(item.get("total", 0)),
                'LineTotalTax': float(item.get("total_tax", 0)),
                'TaxClass': item.get("tax_class"),
                'LineTaxData': str(item.get("taxes", []))
            }
            items.append(subscription_item)
        
        return items
        
    except Exception as e:
        logging.error(f"Fout bij ophalen subscription items voor subscription {subscription_id}: {e}")
        return []


def update_subscription_item(conn: pyodbc.Connection, item: Dict[str, Any]) -> bool:
    """Update een bestaande subscription_item of voeg deze toe als deze niet bestaat"""
    upsert_sql = """
    MERGE subscription_items AS target
    USING (SELECT ? AS SubscriptionItemID) AS source
    ON target.SubscriptionItemID = source.SubscriptionItemID
    WHEN MATCHED THEN
        UPDATE SET
            SubscriptionID = ?,
            SubscriptionItemType = ?,
            SubscriptionItemName = ?,
            ProductID = ?,
            VariationID = ?,
            ProductSKU = ?,
            Quantity = ?,
            LineSubtotal = ?,
            LineSubtotalTax = ?,
            LineTotal = ?,
            LineTotalTax = ?,
            TaxClass = ?,
            LineTaxData = ?
    WHEN NOT MATCHED THEN
        INSERT (
            SubscriptionItemID, SubscriptionID, SubscriptionItemType, SubscriptionItemName,
            ProductID, VariationID, ProductSKU, Quantity, LineSubtotal, LineSubtotalTax,
            LineTotal, LineTotalTax, TaxClass, LineTaxData
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(upsert_sql, (
                # Voor de MATCHED clause
                item['SubscriptionItemID'], item['SubscriptionID'], item['SubscriptionItemType'],
                item['SubscriptionItemName'], item['ProductID'], item['VariationID'],
                item['ProductSKU'], item['Quantity'], item['LineSubtotal'],
                item['LineSubtotalTax'], item['LineTotal'], item['LineTotalTax'],
                item['TaxClass'], item['LineTaxData'],
                # Voor de NOT MATCHED clause
                item['SubscriptionItemID'], item['SubscriptionID'], item['SubscriptionItemType'],
                item['SubscriptionItemName'], item['ProductID'], item['VariationID'],
                item['ProductSKU'], item['Quantity'], item['LineSubtotal'],
                item['LineSubtotalTax'], item['LineTotal'], item['LineTotalTax'],
                item['TaxClass'], item['LineTaxData']
            ))
            return True
    except Exception as e:
        logging.error(f"Fout bij updaten subscription item {item['SubscriptionItemID']}: {e}")
        return False


def get_subscription_ids_from_db(conn: pyodbc.Connection) -> List[int]:
    """Haal alle unieke subscription IDs op uit de database"""
    query = "SELECT DISTINCT SubscriptionID FROM SubscriptionItems ORDER BY SubscriptionID"
    
    subscription_ids = []
    with conn.cursor() as cursor:
        cursor.execute(query)
        for row in cursor.fetchall():
            subscription_ids.append(row[0])
    
    return subscription_ids


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    try:
        # Database configuratie
        db_config = get_config_from_env()
        conn = connect_azuresql(db_config)
        logging.info("Database verbinding gemaakt")
        
        # WooCommerce configuratie
        woo_url, woo_key, woo_secret = get_woo_config_from_env()
        woo_client = WooClient(woo_url, woo_key, woo_secret)
        logging.info("WooCommerce client geïnitialiseerd")
        
        # Haal bestaande subscription_items op
        existing_items = get_existing_subscription_items(conn)
        
        # Haal alle subscription IDs op
        subscription_ids = get_subscription_ids_from_db(conn)
        logging.info(f"Gevonden {len(subscription_ids)} subscriptions om bij te werken")
        
        updated_count = 0
        error_count = 0
        
        for subscription_id in subscription_ids:
            try:
                logging.info(f"Bijwerken van subscription {subscription_id}")
                
                # Haal subscription items op vanuit WooCommerce
                woo_items = get_subscription_items_from_woo(woo_client, subscription_id)
                
                if not woo_items:
                    logging.warning(f"Geen items gevonden voor subscription {subscription_id}")
                    continue
                
                # Update elk item
                for item in woo_items:
                    if update_subscription_item(conn, item):
                        updated_count += 1
                    else:
                        error_count += 1
                
                # Commit na elke subscription
                conn.commit()
                
            except Exception as e:
                logging.error(f"Fout bij bijwerken van subscription {subscription_id}: {e}")
                error_count += 1
                continue
        
        logging.info(f"Bijwerken voltooid. {updated_count} items bijgewerkt, {error_count} fouten")
        
    except Exception as e:
        logging.error(f"Fout: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
