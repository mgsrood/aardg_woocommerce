#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

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


def map_woo_product_to_row(p: dict) -> Optional[Tuple]:
    try:
        product_id = int(p.get("id"))
    except Exception:
        return None
    name = p.get("name") or ""
    status = p.get("status") or "unknown"
    sku = p.get("sku") or None
    regular_price = float(p.get("regular_price") or 0)
    sale_price = float(p.get("sale_price")) if p.get("sale_price") not in (None, "") else None
    tax_class = p.get("tax_class") or None
    date_created = parse_dt(p.get("date_created"))
    date_modified = parse_dt(p.get("date_modified"))
    product_type = p.get("type") or None

    if name == "" or date_created is None or date_modified is None:
        return None

    # Woo heeft geen ProductTypeTaxonomyID direct → NULL laten
    return (
        product_id,
        name,
        status,
        None,
        sku,
        regular_price,
        sale_price,
        tax_class,
        date_created,
        date_modified,
        product_type,
    )


def upsert(cursor: pyodbc.Cursor, rows: List[Tuple]) -> int:
    affected = 0
    for r in rows:
        cursor.execute(
            """
            UPDATE [dbo].[Products]
               SET [Name]=?,[Status]=?,[ProductTypeTaxonomyID]=?,[SKU]=?,[RegularPrice]=?,[SalePrice]=?,[TaxClass]=?,[CreatedDate]=?,[ModifiedDate]=?,[ProductType]=?
             WHERE [ProductID]=?
            """,
            r[1], r[2], r[3], r[4], float(r[5]), float(r[6]) if r[6] is not None else None, r[7], r[8], r[9], r[10], r[0]
        )
        if cursor.rowcount and cursor.rowcount > 0:
            affected += cursor.rowcount
            continue
        cursor.execute(
            """
            INSERT INTO [dbo].[Products] (
                [ProductID],[Name],[Status],[ProductTypeTaxonomyID],[SKU],[RegularPrice],[SalePrice],[TaxClass],[CreatedDate],[ModifiedDate],[ProductType]
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            r[0], r[1], r[2], r[3], r[4], float(r[5]), float(r[6]) if r[6] is not None else None, r[7], r[8], r[9], r[10]
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
            for page in woo.paginate("products", params={"orderby": "date", "order": "asc"}, per_page=100):
                pages += 1
                page_len = len(page) if isinstance(page, list) else 0
                fetched_total += page_len
                logging.info("Products page %d: fetched=%d (running=%d)", pages, page_len, fetched_total)
                rows = [r for r in (map_woo_product_to_row(p) for p in page) if r is not None]
                mapped_total += len(rows)
                logging.info("Products page %d: mapped=%d (running=%d)", pages, len(rows), mapped_total)
                if not rows:
                    continue
                upserted = upsert(cur, rows)
                total += upserted
                conn.commit()
                logging.info("Products page %d: upserted=%d (running=%d)", pages, upserted, total)
        if pages == 0 or fetched_total == 0:
            logging.warning("Products: geen data opgehaald.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Products klaar; pages=%d fetched=%d mapped=%d upserted=%d", pages, fetched_total, mapped_total, total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
