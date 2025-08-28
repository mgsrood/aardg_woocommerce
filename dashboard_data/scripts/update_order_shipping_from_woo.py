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
            UPDATE [dbo].[OrderShipping]
               SET [ShippingMethod]=?,[ShippingCost]=?,[ShippingTax]=?
             WHERE [ShippingItemID]=? AND [OrderID]=?
            """,
            r[2], float(r[3]), float(r[4]), r[0], r[1]
        )
        if cursor.rowcount and cursor.rowcount > 0:
            affected += cursor.rowcount
            continue
        cursor.execute(
            """
            INSERT INTO [dbo].[OrderShipping] ([ShippingItemID],[OrderID],[ShippingMethod],[ShippingCost],[ShippingTax])
            VALUES (?,?,?,?,?)
            """,
            r[0], r[1], r[2], float(r[3]), float(r[4])
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
            logging.info("Order shipping lookback since=%s (UTC)", since)
            params = {"orderby": "date", "order": "asc", "_fields": "id,shipping_lines", "after": since, "modified_after": since}
            for page in woo.paginate("orders", params=params, per_page=100):
                pages += 1
                page_len = len(page) if isinstance(page, list) else 0
                fetched_total += page_len
                logging.info("Order shipping page %d: fetched orders=%d (running=%d)", pages, page_len, fetched_total)
                rows: List[Tuple] = []
                for o in page:
                    order_id = int(o.get("id"))
                    for sl in (o.get("shipping_lines") or []):
                        shipping_item_id = int(sl.get("id"))
                        method = sl.get("method_title") or sl.get("method_id") or "shipping"
                        cost = to_decimal((sl.get("total")))
                        tax = to_decimal((sl.get("total_tax")))
                        rows.append((shipping_item_id, order_id, method, cost, tax))
                logging.info("Order shipping page %d: mapped shipping rows=%d", pages, len(rows))
                if rows:
                    upserted = upsert(cur, rows)
                    total += upserted
                    conn.commit()
                    logging.info("Order shipping page %d: upserted=%d (running=%d)", pages, upserted, total)
                    mapped_total += len(rows)
        if pages == 0 or fetched_total == 0:
            logging.warning("Order shipping: geen data opgehaald in de lookback-periode.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Order shipping klaar; pages=%d fetched_orders=%d mapped_rows=%d upserted=%d", pages, fetched_total, mapped_total, total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
