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


def parse_dt(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    v = value.strip()
    # epoch fallback
    if v.isdigit() and len(v) <= 10:
        try:
            from datetime import datetime, timezone
            ts = int(v)
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    try:
        return date_parser.parse(v).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def read_rows(csv_path: str) -> Iterator[Tuple[int, str, str, str, Optional[int], Optional[str], Optional[str], str, Optional[str], Decimal, Decimal, Decimal, Decimal, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [
            "OrderID","OrderDate","OrderStatus","OrderModified","CustomerUserID","OrderKey","OrderTotal","OrderTax","OrderShipping","OrderShippingTax","Currency","PaymentMethod","CreatedVia","BillingFirstName","BillingLastName","BillingEmail","BillingPhone","BillingCompany","BillingAddress1","BillingAddress2","BillingCity","BillingPostcode","BillingCountry","ShippingFirstName","ShippingLastName","ShippingCompany","ShippingAddress1","ShippingAddress2","ShippingCity","ShippingPostcode","ShippingCountry"
        ]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor orders")
        for row in reader:
            order_id = parse_int(row.get("OrderID"), allow_zero=False)
            if order_id is None:
                continue
            order_date = parse_dt(row.get("OrderDate"))
            order_modified = parse_dt(row.get("OrderModified"))
            order_status = (row.get("OrderStatus") or "").strip() or "unknown"
            customer_id = parse_int(row.get("CustomerUserID"), allow_zero=False)
            order_key = None if is_nullish(row.get("OrderKey")) else (row.get("OrderKey") or "").strip()
            order_number = None  # OrderNumber niet in orders2.csv, altijd None
            currency = (row.get("Currency") or "").strip() or "EUR"
            payment_method = None if is_nullish(row.get("PaymentMethod")) else (row.get("PaymentMethod") or "").strip()
            order_total = parse_decimal(row.get("OrderTotal"))
            order_tax = parse_decimal(row.get("OrderTax"))
            order_shipping = parse_decimal(row.get("OrderShipping"))
            order_shipping_tax = parse_decimal(row.get("OrderShippingTax"))
            date_completed = None  # DateCompleted niet in orders2.csv, altijd None
            date_paid = None  # DatePaid niet in orders2.csv, altijd None
            created_via = None if is_nullish(row.get("CreatedVia")) else (row.get("CreatedVia") or "").strip()
            b_fn = None if is_nullish(row.get("BillingFirstName")) else (row.get("BillingFirstName") or "").strip()
            b_ln = None if is_nullish(row.get("BillingLastName")) else (row.get("BillingLastName") or "").strip()
            b_email = None if is_nullish(row.get("BillingEmail")) else (row.get("BillingEmail") or "").strip()
            b_phone = None if is_nullish(row.get("BillingPhone")) else (row.get("BillingPhone") or "").strip()
            b_company = None if is_nullish(row.get("BillingCompany")) else (row.get("BillingCompany") or "").strip()
            b_addr1 = None if is_nullish(row.get("BillingAddress1")) else (row.get("BillingAddress1") or "").strip()
            b_addr2 = None if is_nullish(row.get("BillingAddress2")) else (row.get("BillingAddress2") or "").strip()
            b_city = None if is_nullish(row.get("BillingCity")) else (row.get("BillingCity") or "").strip()
            b_post = None if is_nullish(row.get("BillingPostcode")) else (row.get("BillingPostcode") or "").strip()
            b_country = None if is_nullish(row.get("BillingCountry")) else (row.get("BillingCountry") or "").strip()
            s_fn = None if is_nullish(row.get("ShippingFirstName")) else (row.get("ShippingFirstName") or "").strip()
            s_ln = None if is_nullish(row.get("ShippingLastName")) else (row.get("ShippingLastName") or "").strip()
            s_company = None if is_nullish(row.get("ShippingCompany")) else (row.get("ShippingCompany") or "").strip()
            s_addr1 = None if is_nullish(row.get("ShippingAddress1")) else (row.get("ShippingAddress1") or "").strip()
            s_addr2 = None if is_nullish(row.get("ShippingAddress2")) else (row.get("ShippingAddress2") or "").strip()
            s_city = None if is_nullish(row.get("ShippingCity")) else (row.get("ShippingCity") or "").strip()
            s_post = None if is_nullish(row.get("ShippingPostcode")) else (row.get("ShippingPostcode") or "").strip()
            s_country = None if is_nullish(row.get("ShippingCountry")) else (row.get("ShippingCountry") or "").strip()

            if order_date is None or order_modified is None:
                continue

            yield (
                order_id,
                order_date,
                order_modified,
                order_status,
                customer_id,
                order_key,
                order_number,
                currency,
                payment_method,
                order_total,
                order_tax,
                order_shipping,
                order_shipping_tax,
                date_completed,
                date_paid,
                created_via,
                b_fn,
                b_ln,
                b_email,
                b_phone,
                b_company,
                b_addr1,
                b_addr2,
                b_city,
                b_post,
                b_country,
                s_fn,
                s_ln,
                s_company,
                s_addr1,
                s_addr2,
                s_city,
                s_post,
                s_country,
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
        cur.execute("TRUNCATE TABLE [dbo].[Orders]")
    except Exception:
        cur.execute("DELETE FROM [dbo].[Orders]")


def bulk_insert(cur: pyodbc.Cursor, rows: List[Tuple]) -> int:
    sql = (
        "INSERT INTO [dbo].[Orders] ("
        "[OrderID],[OrderDate],[OrderModified],[OrderStatus],[CustomerID],[OrderKey],[OrderNumber],[Currency],[PaymentMethod],"
        "[OrderTotal],[OrderTax],[OrderShipping],[OrderShippingTax],[DateCompleted],[DatePaid],"
        "[BillingFirstName],[BillingLastName],[BillingEmail],[BillingPhone],[BillingCompany],[BillingAddress1],[BillingAddress2],[BillingCity],[BillingPostcode],[BillingCountry],"
        "[ShippingFirstName],[ShippingLastName],[ShippingCompany],[ShippingAddress1],[ShippingAddress2],[ShippingCity],[ShippingPostcode],[ShippingCountry],[CreatedVia]"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    cur.fast_executemany = True
    cur.executemany(sql, [(
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], float(r[9]), float(r[10]), float(r[11]), float(r[12]), r[13], r[14],
        r[16], r[17], r[18], r[19], r[20], r[21], r[22], r[23], r[24], r[25], r[26], r[27], r[28], r[29], r[30], r[31], r[32], r[33], r[15]
    ) for r in rows])
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    csv_path = os.environ.get("CSV_PATH_ORDERS", "/Users/maxrood/werk/greit/klanten/aardg_nieuw/csv/orders2.csv")
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
