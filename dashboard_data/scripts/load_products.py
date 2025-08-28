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


def parse_decimal(value: Optional[str]) -> Optional[Decimal]:
    if is_nullish(value):
        return None
    try:
        return Decimal(value.strip())
    except (InvalidOperation, ValueError):
        return None


def parse_dt(value: Optional[str]) -> Optional[str]:
    if is_nullish(value):
        return None
    try:
        return date_parser.parse(value.strip()).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def read_rows(csv_path: str) -> Iterator[Tuple[int, str, str, Optional[int], Optional[str], Decimal, Optional[Decimal], Optional[str], str, str, Optional[str]]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = [
            "ProductID","Name","Status","ProductTypeTaxonomyID","SKU","RegularPrice","SalePrice","TaxClass","CreatedDate","ModifiedDate","ProductType"
        ]
        if reader.fieldnames is None or any(col not in reader.fieldnames for col in required):
            raise SystemExit("CSV mist vereiste kolommen voor products")
        for row in reader:
            product_id = parse_int(row.get("ProductID"), allow_zero=False)
            if product_id is None:
                continue
            name = (row.get("Name") or "").strip()
            status = (row.get("Status") or "").strip() or "unknown"
            product_type_taxonomy_id = parse_int(row.get("ProductTypeTaxonomyID"), allow_zero=False)
            sku = None if is_nullish(row.get("SKU")) else (row.get("SKU") or "").strip()
            regular_price = parse_decimal(row.get("RegularPrice")) or Decimal("0")
            sale_price = parse_decimal(row.get("SalePrice"))
            tax_class = None if is_nullish(row.get("TaxClass")) else (row.get("TaxClass") or "").strip()
            created_date = parse_dt(row.get("CreatedDate"))
            modified_date = parse_dt(row.get("ModifiedDate"))
            product_type = None if is_nullish(row.get("ProductType")) else (row.get("ProductType") or "").strip()
            if name == "" or created_date is None or modified_date is None:
                continue
            yield (
                product_id,
                name,
                status,
                product_type_taxonomy_id,
                sku,
                regular_price,
                sale_price,
                tax_class,
                created_date,
                modified_date,
                product_type,
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
        cur.execute("TRUNCATE TABLE [dbo].[Products]")
    except Exception:
        cur.execute("DELETE FROM [dbo].[Products]")


def bulk_insert(cur: pyodbc.Cursor, rows: List[Tuple]) -> int:
    sql = (
        "INSERT INTO [dbo].[Products] ("
        "[ProductID],[Name],[Status],[ProductTypeTaxonomyID],[SKU],[RegularPrice],[SalePrice],[TaxClass],[CreatedDate],[ModifiedDate],[ProductType]"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?)"
    )
    cur.fast_executemany = True
    cur.executemany(sql, [(
        r[0], r[1], r[2], r[3], r[4], float(r[5]), float(r[6]) if r[6] is not None else None, r[7], r[8], r[9], r[10]
    ) for r in rows])
    return len(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    csv_path = os.environ.get("CSV_PATH_PRODUCTS", "/Users/maxrood/werk/greit/klanten/aardg_nieuw/csv/products.csv")
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
