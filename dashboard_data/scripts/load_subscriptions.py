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
from dateutil import parser as date_parser

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


def parse_dt(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    try:
        return date_parser.parse(value.strip()).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def read_rows(csv_path: str) -> Iterator[Tuple[int, str, Optional[int], Optional[str], int, str, str, Optional[str], Optional[str]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [
            "SubscriptionID","Status","CustomerID","BillingEmail","BillingInterval","BillingPeriod","StartDate","NextPaymentDate","EndDate"
        ]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor subscriptions")
        for row in reader:
            subscription_id = parse_int(row.get("SubscriptionID"), allow_zero=False)
            if subscription_id is None:
                continue
            status = (row.get("Status") or "").strip() or "unknown"
            customer_id = parse_int(row.get("CustomerID"), allow_zero=False)
            billing_email = None if is_nullish(row.get("BillingEmail")) else (row.get("BillingEmail") or "").strip()
            billing_interval = parse_int(row.get("BillingInterval"), allow_zero=False) or 0
            billing_period = (row.get("BillingPeriod") or "").strip() or "month"
            start_date = parse_dt(row.get("StartDate"))
            next_payment_date = parse_dt(row.get("NextPaymentDate"))
            end_raw = row.get("EndDate")
            end_date = None if is_nullish(end_raw) or (end_raw and end_raw.strip() == "0") else parse_dt(end_raw)

            if start_date is None:
                continue

            yield (
                subscription_id,
                status,
                customer_id,
                billing_email,
                billing_interval,
                billing_period,
                start_date,
                next_payment_date,
                end_date,
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
        cur.execute("TRUNCATE TABLE [dbo].[Subscriptions]")
    except Exception:
        cur.execute("DELETE FROM [dbo].[Subscriptions]")


def bulk_insert(cur: pyodbc.Cursor, rows: List[Tuple]) -> int:
    sql = (
        "INSERT INTO [dbo].[Subscriptions] ("
        "[SubscriptionID],[Status],[CustomerID],[BillingEmail],[BillingInterval],[BillingPeriod],[StartDate],[NextPaymentDate],[EndDate]"
        ") VALUES (?,?,?,?,?,?,?,?,?)"
    )
    cur.fast_executemany = True
    cur.executemany(sql, rows)
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    csv_path = os.environ.get(
        "CSV_PATH_SUBSCRIPTIONS",
        "/Users/maxrood/werk/greit/klanten/aardg_nieuw/csv/subscriptions.csv",
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
            for batch in chunked(read_rows(csv_path), size=5000):
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
