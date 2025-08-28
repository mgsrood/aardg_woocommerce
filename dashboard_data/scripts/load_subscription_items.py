#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import sys
import logging
from dataclasses import dataclass
from typing import Iterable, Iterator, List, Optional, Tuple

import pyodbc
from dotenv import load_dotenv

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


def is_nullish(value: Optional[str]) -> bool:
    if value is None:
        return True
    v = value.strip()
    return v == "" or v.upper() == "NULL"


def parse_int(value: Optional[str], allow_zero: bool = False) -> Optional[int]:
    if is_nullish(value):
        return None
    try:
        n = int(value.strip())
        if not allow_zero and n == 0:
            return None
        return n
    except ValueError:
        return None


def parse_decimal(value: Optional[str]) -> Optional[float]:
    if is_nullish(value):
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def read_rows(csv_path: str) -> Iterator[Tuple[int, int, str, str, Optional[int], Optional[int], Optional[str], int, Optional[float], Optional[float], Optional[float], Optional[float], Optional[str], Optional[str]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [
            "SubscriptionItemID", "SubscriptionID", "SubscriptionItemType", "SubscriptionItemName",
            "ProductID", "VariationID", "ProductSKU", "Quantity", "LineSubtotal", "LineSubtotalTax",
            "LineTotal", "LineTotalTax", "TaxClass", "LineTaxData"
        ]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor subscription_items")
        
        for row in reader:
            subscription_item_id = parse_int(row.get("SubscriptionItemID"), allow_zero=False)
            if subscription_item_id is None:
                continue
            
            subscription_id = parse_int(row.get("SubscriptionID"), allow_zero=False)
            if subscription_id is None:
                continue
            
            subscription_item_type = (row.get("SubscriptionItemType") or "").strip() or "line_item"
            subscription_item_name = (row.get("SubscriptionItemName") or "").strip() or ""
            product_id = parse_int(row.get("ProductID"), allow_zero=True)
            variation_id = parse_int(row.get("VariationID"), allow_zero=True)
            product_sku = None if is_nullish(row.get("ProductSKU")) else (row.get("ProductSKU") or "").strip()
            quantity = parse_int(row.get("Quantity"), allow_zero=True) or 1
            
            line_subtotal = parse_decimal(row.get("LineSubtotal"))
            line_subtotal_tax = parse_decimal(row.get("LineSubtotalTax"))
            line_total = parse_decimal(row.get("LineTotal"))
            line_total_tax = parse_decimal(row.get("LineTotalTax"))
            
            tax_class = None if is_nullish(row.get("TaxClass")) else (row.get("TaxClass") or "").strip()
            line_tax_data = None if is_nullish(row.get("LineTaxData")) else (row.get("LineTaxData") or "").strip()
            
            yield (
                subscription_item_id, subscription_id, subscription_item_type, subscription_item_name,
                product_id, variation_id, product_sku, quantity, line_subtotal, line_subtotal_tax,
                line_total, line_total_tax, tax_class, line_tax_data
            )


def create_table(conn: pyodbc.Connection) -> None:
    create_sql = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='SubscriptionItems' AND xtype='U')
    CREATE TABLE SubscriptionItems (
        SubscriptionItemID INT PRIMARY KEY,
        SubscriptionID INT NOT NULL,
        SubscriptionItemType NVARCHAR(50),
        SubscriptionItemName NVARCHAR(500),
        ProductID INT,
        VariationID INT,
        ProductSKU NVARCHAR(100),
        Quantity INT,
        LineSubtotal DECIMAL(10,2),
        LineSubtotalTax DECIMAL(10,2),
        LineTotal DECIMAL(10,2),
        LineTotalTax DECIMAL(10,2),
        TaxClass NVARCHAR(100),
        LineTaxData NVARCHAR(MAX)
    )
    """
    with conn.cursor() as cursor:
        cursor.execute(create_sql)
        conn.commit()
        logging.info("Tabel SubscriptionItems aangemaakt of bestond al")


def clear_table(conn: pyodbc.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM SubscriptionItems")
        conn.commit()
        logging.info("Tabel SubscriptionItems geleegd")


def insert_rows(conn: pyodbc.Connection, rows: Iterable[Tuple[int, int, str, str, Optional[int], Optional[int], Optional[str], int, Optional[float], Optional[float], Optional[float], Optional[float], Optional[str], Optional[str]]]) -> None:
    insert_sql = """
    INSERT INTO SubscriptionItems (
        SubscriptionItemID, SubscriptionID, SubscriptionItemType, SubscriptionItemName,
        ProductID, VariationID, ProductSKU, Quantity, LineSubtotal, LineSubtotalTax,
        LineTotal, LineTotalTax, TaxClass, LineTaxData
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    with conn.cursor() as cursor:
        batch_size = 1000
        batch = []
        total_inserted = 0
        
        for row in rows:
            batch.append(row)
            
            if len(batch) >= batch_size:
                cursor.executemany(insert_sql, batch)
                total_inserted += len(batch)
                batch = []
                logging.info(f"Batch van {batch_size} rijen ingevoegd, totaal: {total_inserted}")
        
        # Laatste batch
        if batch:
            cursor.executemany(insert_sql, batch)
            total_inserted += len(batch)
            logging.info(f"Laatste batch van {len(batch)} rijen ingevoegd, totaal: {total_inserted}")
        
        conn.commit()
        logging.info(f"Totaal {total_inserted} subscription_items ingevoegd")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    if len(sys.argv) != 2:
        print("Gebruik: python load_subscription_items.py <csv_bestand>")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    if not os.path.exists(csv_path):
        logging.error(f"CSV bestand niet gevonden: {csv_path}")
        sys.exit(1)
    
    try:
        config = get_config_from_env()
        conn = connect_azuresql(config)
        
        logging.info("Database verbinding gemaakt")
        
        # Tabel aanmaken als deze niet bestaat
        create_table(conn)
        
        # Tabel legen
        clear_table(conn)
        
        # Rijen inlezen en invoegen
        rows = read_rows(csv_path)
        insert_rows(conn, rows)
        
        logging.info("Klaar met laden van SubscriptionItems")
        
    except Exception as e:
        logging.error(f"Fout: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
