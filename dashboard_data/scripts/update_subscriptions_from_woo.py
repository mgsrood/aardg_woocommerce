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


def map_subscription(s: dict) -> Optional[Tuple]:
    try:
        sub_id = int(s.get("id"))
    except Exception:
        return None
    status = s.get("status") or "unknown"
    customer_id = int((s.get("customer_id") or 0)) or None
    billing_email = None
    try:
        billing_email = (s.get("billing" ) or {}).get("email") or None
    except Exception:
        pass

    interval = int((s.get("billing_interval") or 0)) or 0
    period = s.get("billing_period") or "month"

    start_date = parse_dt(s.get("date_created_gmt") or s.get("start_date_gmt"))
    next_payment = parse_dt(s.get("next_payment_date_gmt") or s.get("next_payment_gmt"))
    end_date = parse_dt(s.get("end_date_gmt") or s.get("date_completed_gmt"))

    # Probeer meer datumvelden voor start_date als de standaard velden niet werken
    if start_date is None:
        start_date = parse_dt(s.get("date_created") or s.get("start_date") or s.get("date") or s.get("created_at"))
    
    # Probeer meer datumvelden voor next_payment
    if next_payment is None:
        next_payment = parse_dt(s.get("next_payment_date") or s.get("next_payment") or s.get("next_payment_gmt"))
    
    # Probeer meer datumvelden voor end_date
    if end_date is None:
        end_date = parse_dt(s.get("end_date") or s.get("date_completed") or s.get("completed_at"))

    # Debug logging voor eerste subscription
    if sub_id == 1:  # Eerste subscription
        logging.info("DEBUG: Eerste subscription velden: %s", list(s.keys()))
        logging.info("DEBUG: date_created_gmt=%s, start_date_gmt=%s", s.get("date_created_gmt"), s.get("start_date_gmt"))
        logging.info("DEBUG: date_created=%s, start_date=%s", s.get("date_created"), s.get("start_date"))
        logging.info("DEBUG: parsed start_date=%s", start_date)

    if start_date is None:
        logging.debug("DEBUG: Subscription %d gefilterd - start_date is None", sub_id)
        return None
    return (
        sub_id,
        status,
        customer_id,
        billing_email,
        interval,
        period,
        start_date,
        next_payment,
        end_date,
    )


def upsert(cursor: pyodbc.Cursor, rows: List[Tuple]) -> int:
    affected = 0
    for r in rows:
        cursor.execute(
            """
            UPDATE [dbo].[Subscriptions]
               SET [Status]=?,[CustomerID]=?,[BillingEmail]=?,[BillingInterval]=?,[BillingPeriod]=?,[StartDate]=?,[NextPaymentDate]=?,[EndDate]=?
             WHERE [SubscriptionID]=?
            """,
            r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[0]
        )
        if cursor.rowcount and cursor.rowcount > 0:
            affected += cursor.rowcount
            continue
        cursor.execute(
            """
            INSERT INTO [dbo].[Subscriptions] ([SubscriptionID],[Status],[CustomerID],[BillingEmail],[BillingInterval],[BillingPeriod],[StartDate],[NextPaymentDate],[EndDate])
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8]
        )
        affected += 1
    return affected


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Subscriptions plugin endpoints zitten onder wc/v1/subscriptions of wc/v3/subscriptions afhankelijk van plugin
    api_version = os.environ.get("WOO_SUBSCRIPTIONS_API_VERSION", "wc/v1")

    woo = WooClient(
        base_url=os.environ["WOO_BASE_URL"],
        consumer_key=os.environ["WOO_CONSUMER_KEY"],
        consumer_secret=os.environ["WOO_CONSUMER_SECRET"],
        api_version=api_version,
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
            for page in woo.paginate("subscriptions", params={"orderby": "date", "order": "asc"}, per_page=100):
                pages += 1
                page_len = len(page) if isinstance(page, list) else 0
                fetched_total += page_len
                logging.info("Subscriptions page %d: fetched=%d (running=%d)", pages, page_len, fetched_total)
                rows = [r for r in (map_subscription(s) for s in page) if r is not None]
                mapped_total += len(rows)
                logging.info("Subscriptions page %d: mapped=%d (running=%d)", pages, len(rows), mapped_total)
                if not rows:
                    continue
                upserted = upsert(cur, rows)
                total += upserted
                conn.commit()
                logging.info("Subscriptions page %d: upserted=%d (running=%d)", pages, upserted, total)
        if pages == 0 or fetched_total == 0:
            logging.warning("Subscriptions: geen data opgehaald.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    logging.info("Subscriptions klaar; api=%s pages=%d fetched=%d mapped=%d upserted=%d", api_version, pages, fetched_total, mapped_total, total)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Afgebroken door gebruiker", file=sys.stderr)
        sys.exit(130)
