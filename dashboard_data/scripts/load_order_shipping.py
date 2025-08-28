#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import sys
import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
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
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};UID={cfg.username};PWD={cfg.password};"
        f"Encrypt={cfg.encrypt};TrustServerCertificate={cfg.trust_server_certificate};Connection Timeout=30;"
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


def parse_decimal(value: Optional[str]) -> Decimal:
    if is_nullish(value):
        return Decimal("0")
    try:
        return Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def read_rows(csv_path: str) -> Iterator[Tuple[int, int, str, Decimal, Decimal]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = ["ShippingItemID","OrderID","ShippingMethod","ShippingCost","ShippingTax"]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor order_shipping")
        for row in reader:
            shipping_item_id = parse_int(row.get("ShippingItemID"))
            order_id = parse_int(row.get("OrderID"))
            method = (row.get("ShippingMethod") or "").strip()
            cost = parse_decimal(row.get("ShippingCost"))
            tax = parse_decimal(row.get("ShippingTax"))
            if shipping_item_id is None or order_id is None or method == "":
                continue
            yield (shipping_item_id, order_id, method, cost, tax)


def chunked(iterable: Iterable, size: int) -> Iterator[list]:
    chunk: list = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def maybe_truncate(cur: pyodbc.Cursor) -> None:
    if os.environ.get("TRUNCATE_BEFORE_LOAD", "0") not in ("1", "true", "TRUE", "yes", "YES"):
        return
    try:
        cur.execute("TRUNCATE TABLE [dbo].[OrderShipping]")
    except Exception:
        cur.execute("DELETE FROM [dbo].[OrderShipping]")


def bulk_insert(cur: pyodbc.Cursor, rows: List[Tuple[int, int, str, Decimal, Decimal]]) -> int:
    sql = (
        "INSERT INTO [dbo].[OrderShipping] ([ShippingItemID],[OrderID],[ShippingMethod],[ShippingCost],[ShippingTax]) "
        "VALUES (?,?,?,?,?)"
    )
    cur.fast_executemany = True
    cur.executemany(sql, [(r[0], r[1], r[2], float(r[3]), float(r[4])) for r in rows])
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    csv_path = os.environ.get(
        "CSV_PATH_ORDER_SHIPPING",
        "/Users/maxrood/werk/greit/klanten/aardg_nieuw/csv/order_shipping.csv",
    )
    if not os.path.isfile(csv_path):
        raise SystemExit(f"CSV niet gevonden: {csv_path}")

    cfg = get_config_from_env()
    conn = connect_azuresql(cfg)
    conn.autocommit = False
    total = 0
    try:
        with conn.cursor() as cur:
            maybe_truncate(cur)
            for batch in chunked(read_rows(csv_path), 5000):
                total += bulk_insert(cur, batch)
                conn.commit()
                logging.info("Batch inserted; totaal=%d", total)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Klaar; inserted rijen: %d", total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
