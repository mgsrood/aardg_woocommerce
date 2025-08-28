#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

import pyodbc
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


def parse_dt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return date_parser.parse(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().lower()
    return v or None


def upsert(cursor: pyodbc.Cursor, rows: List[Tuple]) -> int:
    affected = 0
    for r in rows:
        cursor.execute(
            """
            UPDATE [dbo].[Customers]
               SET [CustomerID]=?,[FirstName]=?,[LastName]=?,[Phone]=?,[Company]=?,[DateRegistered]=?
             WHERE [Email]=?
            """,
            r[0], r[2], r[3], r[4], r[5], r[6], r[1]
        )
        if cursor.rowcount and cursor.rowcount > 0:
            affected += cursor.rowcount
            continue
        cursor.execute(
            """
            INSERT INTO [dbo].[Customers] ([CustomerID],[Email],[FirstName],[LastName],[Phone],[Company],[DateRegistered])
            VALUES (?,?,?,?,?,?,?)
            """,
            r[0], r[1], r[2], r[3], r[4], r[5], r[6]
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
            # Probeer eerst rechtstreeks customers (WooCommerce REST v3)
            try:
                for page in woo.paginate("customers", params={"orderby": "date", "order": "asc"}, per_page=100):
                    pages += 1
                    page_len = len(page) if isinstance(page, list) else 0
                    fetched_total += page_len
                    logging.info("Customers page %d: fetched=%d (running=%d)", pages, page_len, fetched_total)
                    rows: List[Tuple] = []
                    for c in page:
                        email = normalize_email(c.get("email"))
                        if email is None:
                            continue
                        cid = int(c.get("id") or 0) or None
                        first_name = (c.get("first_name") or None) or ((c.get("billing") or {}).get("first_name") or None)
                        last_name = (c.get("last_name") or None) or ((c.get("billing") or {}).get("last_name") or None)
                        phone = ((c.get("billing") or {}).get("phone") or None)
                        company = ((c.get("billing") or {}).get("company") or None)
                        date_registered = parse_dt(c.get("date_created")) or parse_dt(c.get("date_modified")) or parse_dt(c.get("last_order_date")) or parse_dt(c.get("date_last_active"))
                        if date_registered is None:
                            # fallback naar nu mag, maar we laten liever leeg: overslaan
                            continue
                        rows.append((cid, email, first_name, last_name, phone, company, date_registered))
                    logging.info("Customers page %d: mapped=%d", pages, len(rows))
                    if rows:
                        upserted = upsert(cur, rows)
                        total += upserted
                        conn.commit()
                        logging.info("Customers page %d: upserted=%d (running=%d)", pages, upserted, total)
                        mapped_total += len(rows)
            except Exception:
                logging.warning("Customers endpoint niet beschikbaar; val terug op orders → billing emails.")
                # Fallback: verzamel unieke klanten uit orders
                seen: set[str] = set()
                pages = 0
                for page in woo.paginate("orders", params={"orderby": "date", "order": "asc"}, per_page=100):
                    pages += 1
                    page_len = len(page) if isinstance(page, list) else 0
                    fetched_total += page_len
                    logging.info("Orders→customers page %d: fetched orders=%d (running=%d)", pages, page_len, fetched_total)
                    rows: List[Tuple] = []
                    for o in page:
                        b = o.get("billing") or {}
                        email = normalize_email(b.get("email"))
                        if email is None or email in seen:
                            continue
                        seen.add(email)
                        cid = int(o.get("customer_id") or 0) or None
                        first_name = b.get("first_name") or None
                        last_name = b.get("last_name") or None
                        phone = b.get("phone") or None
                        company = b.get("company") or None
                        date_registered = parse_dt(o.get("date_created")) or parse_dt(o.get("date_modified"))
                        if date_registered is None:
                            continue
                        rows.append((cid, email, first_name, last_name, phone, company, date_registered))
                    logging.info("Orders→customers page %d: mapped customers=%d", pages, len(rows))
                    if rows:
                        upserted = upsert(cur, rows)
                        total += upserted
                        conn.commit()
                        logging.info("Orders→customers page %d: upserted=%d (running=%d)", pages, upserted, total)
                        mapped_total += len(rows)
        if pages == 0 or fetched_total == 0:
            logging.warning("Customers: geen data opgehaald.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Customers klaar; pages=%d fetched=%d mapped=%d upserted=%d", pages, fetched_total, mapped_total, total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
