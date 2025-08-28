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


def read_rows(csv_path: str) -> Iterator[Tuple[int, int, str, Optional[float], Optional[float]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [
            "SubscriptionShippingID", "SubscriptionID", "ShippingMethodName", "ShippingCost", "ShippingTax"
        ]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor subscription_shipping")
        
        for row in reader:
            subscription_shipping_id = parse_int(row.get("SubscriptionShippingID"), allow_zero=False)
            if subscription_shipping_id is None:
                continue
            
            subscription_id = parse_int(row.get("SubscriptionID"), allow_zero=False)
            if subscription_id is None:
                continue
            
            shipping_method_name = (row.get("ShippingMethodName") or "").strip() or ""
            shipping_cost = parse_decimal(row.get("ShippingCost"))
            shipping_tax = parse_decimal(row.get("ShippingTax"))
            
            yield (
                subscription_shipping_id, subscription_id, shipping_method_name, shipping_cost, shipping_tax
            )


def create_table(conn: pyodbc.Connection) -> None:
    create_sql = """
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='SubscriptionShipping' AND xtype='U')
    CREATE TABLE SubscriptionShipping (
        SubscriptionShippingID INT PRIMARY KEY,
        SubscriptionID INT NOT NULL,
        ShippingMethodName NVARCHAR(200),
        ShippingCost DECIMAL(10,2),
        ShippingTax DECIMAL(10,2)
    )
    """
    with conn.cursor() as cursor:
        cursor.execute(create_sql)
        conn.commit()
        logging.info("Tabel SubscriptionShipping aangemaakt of bestond al")


def clear_table(conn: pyodbc.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM SubscriptionShipping")
        conn.commit()
        logging.info("Tabel SubscriptionShipping geleegd")


def insert_rows(conn: pyodbc.Connection, rows: Iterable[Tuple[int, int, str, Optional[float], Optional[float]]]) -> None:
    insert_sql = """
    INSERT INTO SubscriptionShipping (
        SubscriptionShippingID, SubscriptionID, ShippingMethodName, ShippingCost, ShippingTax
    ) VALUES (?, ?, ?, ?, ?)
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
        logging.info(f"Totaal {total_inserted} subscription shipping records ingevoegd")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    if len(sys.argv) != 2:
        print("Gebruik: python load_subscription_shipping.py <csv_bestand>")
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
        
        logging.info("Klaar met laden van SubscriptionShipping")
        
    except Exception as e:
        logging.error(f"Fout: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    main()
