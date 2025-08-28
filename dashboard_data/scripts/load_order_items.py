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


def parse_int(value: Optional[str], allow_zero: bool = True) -> Optional[int]:
    if is_nullish(value):
        return None
    try:
        num = int(value.strip())
        if not allow_zero and num == 0:
            return None
        return num
    except ValueError:
        return None


def parse_decimal(value: Optional[str]) -> Decimal:
    if is_nullish(value):
        return Decimal("0")
    try:
        return Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def read_rows(csv_path: str) -> Iterator[Tuple[int, int, str, str, Optional[int], Optional[int], Optional[str], int, Decimal, Decimal, Decimal, Decimal, Optional[str]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [
            "OrderItemID","OrderID","OrderItemType","OrderItemName","ProductID","VariationID","SKU","Quantity","LineSubtotal","LineSubtotalTax","LineTotal","LineTotalTax","TaxClass"
        ]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor order_items")

        for row in reader:
            order_item_id = parse_int(row.get("OrderItemID"), allow_zero=False)
            order_id = parse_int(row.get("OrderID"), allow_zero=False)
            if order_item_id is None or order_id is None:
                continue

            order_item_type = (row.get("OrderItemType") or "").strip()
            order_item_name = (row.get("OrderItemName") or "").strip()
            product_id = parse_int(row.get("ProductID"), allow_zero=False)
            variation_id = parse_int(row.get("VariationID"), allow_zero=False)
            sku = None if is_nullish(row.get("SKU")) else (row.get("SKU") or "").strip()
            quantity = parse_int(row.get("Quantity"), allow_zero=False) or 0
            line_subtotal = parse_decimal(row.get("LineSubtotal"))
            line_subtotal_tax = parse_decimal(row.get("LineSubtotalTax"))
            line_total = parse_decimal(row.get("LineTotal"))
            line_total_tax = parse_decimal(row.get("LineTotalTax"))
            tax_class = None if is_nullish(row.get("TaxClass")) else (row.get("TaxClass") or "").strip()

            if order_item_type == "" or order_item_name == "" or quantity <= 0:
                continue

            yield (
                order_item_id,
                order_id,
                order_item_type,
                order_item_name,
                product_id,
                variation_id,
                sku,
                quantity,
                line_subtotal,
                line_subtotal_tax,
                line_total,
                line_total_tax,
                tax_class,
            )


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
        cur.execute("TRUNCATE TABLE [dbo].[OrderItems]")
    except Exception:
        cur.execute("DELETE FROM [dbo].[OrderItems]")


def bulk_insert(cur: pyodbc.Cursor, rows: List[Tuple[int, int, str, str, Optional[int], Optional[int], Optional[str], int, Decimal, Decimal, Decimal, Decimal, Optional[str]]]) -> int:
    sql = (
        "INSERT INTO [dbo].[OrderItems] ("
        "[OrderItemID],[OrderID],[OrderItemType],[OrderItemName],[ProductID],[VariationID],[SKU],[Quantity],[LineSubtotal],[LineSubtotalTax],[LineTotal],[LineTotalTax],[TaxClass]"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    cur.fast_executemany = True
    cur.executemany(sql, [(
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], float(r[8]), float(r[9]), float(r[10]), float(r[11]), r[12]
    ) for r in rows])
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    csv_path = os.environ.get(
        "CSV_PATH_ORDER_ITEMS",
        "/Users/maxrood/werk/greit/klanten/aardg_nieuw/csv/order_items.csv",
    )
    if not os.path.isfile(csv_path):
        raise SystemExit(f"CSV niet gevonden op pad: {csv_path}")

    cfg = get_config_from_env()
    conn = connect_azuresql(cfg)
    conn.autocommit = False

    total = 0
    try:
        with conn.cursor() as cur:
            maybe_truncate(cur)
            logging.info("Start laden order items uit %s", csv_path)
            for batch in chunked(read_rows(csv_path), size=5000):
                inserted = bulk_insert(cur, batch)
                conn.commit()
                total += inserted
                logging.info("Batch inserted: %d (totaal %d)", inserted, total)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    logging.info("Klaar. Totaal inserted: %d", total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
