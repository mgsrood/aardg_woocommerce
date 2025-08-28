#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import sys
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Iterator, List, Optional, Tuple

import pyodbc
from dateutil import parser as date_parser
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
        missing = exc.args[0]
        raise SystemExit(
            f"Ontbrekende omgevingvariabele: {missing}. Stel AZURE_SQL_SERVER, AZURE_SQL_DATABASE, AZURE_SQL_USERNAME, AZURE_SQL_PASSWORD."
        )


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
    if v == "":
        return True
    if v.upper() == "NULL":
        return True
    return False


def normalize_email(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    return value.strip().lower()


def normalize_name(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    return value.strip()


def normalize_company(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    return value.strip()


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    raw = value.strip()
    if raw.startswith("00"):
        raw = "+" + raw[2:]
    cleaned_chars: List[str] = []
    for i, ch in enumerate(raw):
        if ch.isdigit():
            cleaned_chars.append(ch)
        elif ch == "+" and i == 0:
            cleaned_chars.append(ch)
    cleaned = "".join(cleaned_chars)
    return cleaned or None


def parse_customer_id(value: Optional[str]) -> Optional[int]:
    if is_nullish(value):
        return None
    try:
        num = int(value.strip())
        if num == 0:
            return None
        return num
    except ValueError:
        return None


def parse_dtm(value: Optional[str]) -> Optional[datetime]:
    if is_nullish(value):
        return None
    v = value.strip()
    try:
        dt = date_parser.parse(v)
        return dt
    except Exception:
        return None


def read_rows(csv_path: str) -> Iterator[Tuple[Optional[int], str, Optional[str], Optional[str], Optional[str], Optional[str], datetime]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = ["CustomerID", "Email", "FirstName", "LastName", "Phone", "Company", "DateRegistered"]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen")

        for row in reader:
            customer_id = parse_customer_id(row.get("CustomerID"))
            email = normalize_email(row.get("Email"))
            first_name = normalize_name(row.get("FirstName"))
            last_name = normalize_name(row.get("LastName"))
            phone = normalize_phone(row.get("Phone"))
            company = normalize_company(row.get("Company"))
            date_registered = parse_dtm(row.get("DateRegistered"))

            if email is None or date_registered is None:
                continue

            yield (
                customer_id,
                email,
                first_name,
                last_name,
                phone,
                company,
                date_registered,
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
        cur.execute("TRUNCATE TABLE [dbo].[Customers]")
    except Exception:
        # Fallback wanneer TRUNCATE faalt (bijv. FK): DELETE
        cur.execute("DELETE FROM [dbo].[Customers]")


def bulk_insert(cur: pyodbc.Cursor, rows: List[Tuple[Optional[int], str, Optional[str], Optional[str], Optional[str], Optional[str], datetime]]) -> int:
    sql = (
        "INSERT INTO [dbo].[Customers] ([CustomerID],[Email],[FirstName],[LastName],[Phone],[Company],[DateRegistered]) "
        "VALUES (?,?,?,?,?,?,?)"
    )
    cur.fast_executemany = True
    cur.executemany(sql, rows)
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    csv_path = os.environ.get(
        "CSV_PATH",
        "/Users/maxrood/werk/greit/klanten/aardg_nieuw/csv/customers.csv",
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
            logging.info("Start laden uit %s", csv_path)
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
