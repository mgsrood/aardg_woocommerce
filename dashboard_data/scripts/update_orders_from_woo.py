#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Iterator, List, Optional, Tuple

import pyodbc
from dotenv import load_dotenv
from dateutil import parser as date_parser
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


def map_woo_order_to_row(o: dict) -> Optional[Tuple]:
    try:
        order_id = int(o.get("id"))
    except Exception:
        return None
    status = o.get("status") or "unknown"
    currency = o.get("currency") or "EUR"
    date_created = parse_dt(o.get("date_created"))
    date_modified = parse_dt(o.get("date_modified"))
    date_completed = parse_dt(o.get("date_completed"))
    date_paid = parse_dt(o.get("date_paid"))
    customer_id = int(o.get("customer_id") or 0) or None
    order_key = o.get("order_key")
    number = o.get("number")
    total = to_decimal(o.get("total"))
    total_tax = to_decimal(o.get("total_tax"))
    shipping_total = to_decimal(o.get("shipping_total"))
    shipping_tax = to_decimal(o.get("shipping_tax"))

    b = o.get("billing") or {}
    s = o.get("shipping") or {}

    row = (
        order_id,
        date_created,
        date_modified,
        status,
        customer_id,
        order_key,
        number,
        currency,
        o.get("payment_method"),
        o.get("created_via"),
        total,
        total_tax,
        shipping_total,
        shipping_tax,
        date_completed,
        date_paid,
        b.get("first_name") or None,
        b.get("last_name") or None,
        b.get("email") or None,
        b.get("phone") or None,
        b.get("company") or None,
        b.get("address_1") or None,
        b.get("address_2") or None,
        b.get("city") or None,
        b.get("postcode") or None,
        b.get("country") or None,
        s.get("first_name") or None,
        s.get("last_name") or None,
        s.get("company") or None,
        s.get("address_1") or None,
        s.get("address_2") or None,
        s.get("city") or None,
        s.get("postcode") or None,
        s.get("country") or None,
    )
    if row[1] is None or row[2] is None:
        return None
    return row


def upsert(cursor: pyodbc.Cursor, rows: List[Tuple]) -> int:
    affected = 0
    for r in rows:
        cursor.execute(
            """
            UPDATE [dbo].[Orders]
               SET [OrderDate]=?,[OrderModified]=?,[OrderStatus]=?,[CustomerID]=?,[OrderKey]=?,[OrderNumber]=?,[Currency]=?,[PaymentMethod]=?,[CreatedVia]=?,
                   [OrderTotal]=?,[OrderTax]=?,[OrderShipping]=?,[OrderShippingTax]=?,[DateCompleted]=?,[DatePaid]=?,
                   [BillingFirstName]=?,[BillingLastName]=?,[BillingEmail]=?,[BillingPhone]=?,[BillingCompany]=?,[BillingAddress1]=?,[BillingAddress2]=?,[BillingCity]=?,[BillingPostcode]=?,[BillingCountry]=?,
                   [ShippingFirstName]=?,[ShippingLastName]=?,[ShippingCompany]=?,[ShippingAddress1]=?,[ShippingAddress2]=?,[ShippingCity]=?,[ShippingPostcode]=?,[ShippingCountry]=?
             WHERE [OrderID]=?
            """,
            r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], float(r[10]), float(r[11]), float(r[12]), float(r[13]), r[14], r[15],
            r[16], r[17], r[18], r[19], r[20], r[21], r[22], r[23], r[24], r[25],
            r[26], r[27], r[28], r[29], r[30], r[31], r[32], r[33], r[0]
        )
        if cursor.rowcount and cursor.rowcount > 0:
            affected += cursor.rowcount
            continue
        cursor.execute(
            """
            INSERT INTO [dbo].[Orders] (
                [OrderID],[OrderDate],[OrderModified],[OrderStatus],[CustomerID],[OrderKey],[OrderNumber],[Currency],[PaymentMethod],[CreatedVia],
                [OrderTotal],[OrderTax],[OrderShipping],[OrderShippingTax],[DateCompleted],[DatePaid],
                [BillingFirstName],[BillingLastName],[BillingEmail],[BillingPhone],[BillingCompany],[BillingAddress1],[BillingAddress2],[BillingCity],[BillingPostcode],[BillingCountry],
                [ShippingFirstName],[ShippingLastName],[ShippingCompany],[ShippingAddress1],[ShippingAddress2],[ShippingCity],[ShippingPostcode],[ShippingCountry]
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], float(r[10]), float(r[11]), float(r[12]), float(r[13]), r[14], r[15],
            r[16], r[17], r[18], r[19], r[20], r[21], r[22], r[23], r[24], r[25],
            r[26], r[27], r[28], r[29], r[30], r[31], r[32], r[33]
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
            # Calculate the date 60 days ago (UTC)
            sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)
            since_iso = sixty_days_ago.strftime("%Y-%m-%dT%H:%M:%SZ")
            logging.info("Orders lookback since=%s (UTC)", since_iso)

            for page in woo.paginate(
                "orders",
                params={
                    "after": since_iso,
                    "modified_after": since_iso,
                    "orderby": "date",
                    "order": "asc",
                },
                per_page=100,
            ):
                pages += 1
                page_len = len(page) if isinstance(page, list) else 0
                fetched_total += page_len
                logging.info("Orders page %d: fetched=%d (running=%d)", pages, page_len, fetched_total)
                rows = [r for r in (map_woo_order_to_row(o) for o in page) if r is not None]
                mapped_total += len(rows)
                logging.info("Orders page %d: mapped=%d (running=%d)", pages, len(rows), mapped_total)
                if not rows:
                    continue
                upserted = upsert(cur, rows)
                total += upserted
                conn.commit()
                logging.info("Orders page %d: upserted=%d (running=%d)", pages, upserted, total)
        if pages == 0 or fetched_total == 0:
            logging.warning("Orders: geen data opgehaald in de lookback-periode.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Orders klaar; pages=%d fetched=%d mapped=%d upserted=%d", pages, fetched_total, mapped_total, total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
