#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Tuple

import pyodbc
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

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
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};UID={cfg.username};PWD={cfg.password};"
        f"Encrypt={cfg.encrypt};TrustServerCertificate={cfg.trust_server_certificate};Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


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


def upsert(cursor: pyodbc.Cursor, rows: List[Tuple]) -> int:
    affected = 0
    for r in rows:
        cursor.execute(
            """
            UPDATE [dbo].[OrderItems]
               SET [OrderItemType]=?,[OrderItemName]=?,[ProductID]=?,[VariationID]=?,[SKU]=?,[Quantity]=?,[LineSubtotal]=?,[LineSubtotalTax]=?,[LineTotal]=?,[LineTotalTax]=?,[TaxClass]=?
             WHERE [OrderItemID]=? AND [OrderID]=?
            """,
            r[2], r[3], r[4], r[5], r[6], r[7], float(r[8]), float(r[9]), float(r[10]), float(r[11]), r[12], r[0], r[1]
        )
        if cursor.rowcount and cursor.rowcount > 0:
            affected += cursor.rowcount
            continue
        cursor.execute(
            """
            INSERT INTO [dbo].[OrderItems] (
                [OrderItemID],[OrderID],[OrderItemType],[OrderItemName],[ProductID],[VariationID],[SKU],[Quantity],[LineSubtotal],[LineSubtotalTax],[LineTotal],[LineTotalTax],[TaxClass]
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], float(r[8]), float(r[9]), float(r[10]), float(r[11]), r[12]
        )
        affected += 1
    return affected


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    woo = WooClient(
        base_url=os.environ["WOO_BASE_URL"],
        consumer_key=os.environ["WOO_CONSUMER_KEY"],
        consumer_secret=os.environ["WOO_CONSUMER_SECRET"],
        api_version=os.environ.get("WOO_API_VERSION", "wc/v3"),
        timeout_seconds=float(os.environ.get("WOO_TIMEOUT_SECONDS", "30")),
        rate_limit_sleep_seconds=float(os.environ.get("WOO_RATE_LIMIT_SLEEP_SECONDS", "0")),
    )

    cfg = get_config_from_env()
    conn = connect_azuresql(cfg)
    conn.autocommit = False

    total = 0
    fetched_total = 0
    mapped_total = 0
    pages = 0
    try:
        with conn.cursor() as cur:
            since = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
            logging.info("Order items lookback since=%s (UTC)", since)
            params = {"orderby": "date", "order": "asc", "_fields": "id,line_items", "after": since, "modified_after": since}
            for page in woo.paginate("orders", params=params, per_page=100):
                pages += 1
                page_len = len(page) if isinstance(page, list) else 0
                fetched_total += page_len
                logging.info("Order items page %d: fetched orders=%d (running=%d)", pages, page_len, fetched_total)
                rows: List[Tuple] = []
                for o in page:
                    order_id = int(o.get("id"))
                    for li in (o.get("line_items") or []):
                        order_item_id = int(li.get("id"))
                        order_item_type = "line_item"
                        order_item_name = li.get("name") or ""
                        product_id = int(li.get("product_id") or 0) or None
                        variation_id = int(li.get("variation_id") or 0) or None
                        sku = li.get("sku") or None
                        quantity = int(li.get("quantity") or 0)
                        line_subtotal = to_decimal(li.get("subtotal"))
                        line_subtotal_tax = to_decimal(li.get("subtotal_tax"))
                        line_total = to_decimal(li.get("total"))
                        line_total_tax = to_decimal(li.get("total_tax"))
                        tax_class = li.get("tax_class") or None
                        if order_item_name == "" or quantity <= 0:
                            continue
                        rows.append((
                            order_item_id, order_id, order_item_type, order_item_name, product_id, variation_id, sku, quantity,
                            line_subtotal, line_subtotal_tax, line_total, line_total_tax, tax_class
                        ))
                logging.info("Order items page %d: mapped items=%d", pages, len(rows))
                if rows:
                    upserted = upsert(cur, rows)
                    total += upserted
                    conn.commit()
                    logging.info("Order items page %d: upserted=%d (running=%d)", pages, upserted, total)
                    mapped_total += len(rows)
        if pages == 0 or fetched_total == 0:
            logging.warning("Order items: geen data opgehaald in de lookback-periode.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Order items klaar; pages=%d fetched_orders=%d mapped_items=%d upserted=%d", pages, fetched_total, mapped_total, total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
