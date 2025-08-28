#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta

import pyodbc
import requests
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


@dataclass
class MontaConfig:
    base_url: str
    username: str
    password: str
    timeout_seconds: float = 60.0


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


def get_monta_config_from_env() -> MontaConfig:
    try:
        return MontaConfig(
            base_url=os.environ["MONTA_BASE_URL"],
            username=os.environ["MONTA_USERNAME"],
            password=os.environ["MONTA_PASSWORD"],
            timeout_seconds=float(os.environ.get("MONTA_TIMEOUT", "60.0")),
        )
    except KeyError as exc:
        raise SystemExit(f"Ontbrekende Monta env var: {exc.args[0]}")


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


class MontaClient:
    def __init__(self, config: MontaConfig):
        self.base_url = config.base_url.rstrip("/")
        self.username = config.username
        self.password = config.password
        self.timeout_seconds = config.timeout_seconds
        self.session = requests.Session()
        
        # Gebruik HTTP Basic Authentication
        self.session.auth = (self.username, self.password)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """Maak een GET request naar de Monta API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Fout bij ophalen van {url}: {e}")
            raise

    def get_products_stock_from_sku_list(self, sku_list: List[str]) -> List[Dict[str, Any]]:
        """Haal stock data op voor een lijst van SKUs (zoals in de originele code)"""
        stock_data = []
        
        for sku in sku_list:
            try:
                # Haal stock data op voor dit specifieke product
                stock_endpoint = f"product/{sku}/stock"
                logging.debug(f"Ophalen stock voor SKU: {sku}")
                
                stock_response = self.get(stock_endpoint)
                stock_info = stock_response.json()
                
                # Gebruik de volledige response als data
                stock_data.append(stock_info)
                
            except Exception as e:
                logging.warning(f"Fout bij ophalen stock voor product {sku}: {e}")
                continue
        
        logging.info(f"Succesvol stock data verzameld voor {len(stock_data)} producten")
        return stock_data

    def get_stock_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None, sku_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Haal stock data op - gebruik SKU lijst of default lijst"""
        
        if sku_list:
            return self.get_products_stock_from_sku_list(sku_list)
        
        # Default SKU lijst (gebaseerd op de originele dictionaries.py)
        default_skus = [
            "8719326399355",  # citroen
            "8719326399362",  # bloem
            "8719326399379",  # gember
            "8719326399386",  # kombucha
            "8719326399393",  # waterkefir
            "8719327215111",  # starter
            "8719327215128",  # frisdrank_mix
            "8719327215135",  # mix_originals
            "8719327215180",  # probiotica
        ]
        
        logging.info(f"Gebruik default SKU lijst met {len(default_skus)} producten")
        return self.get_products_stock_from_sku_list(default_skus)


def get_standardised_product_name(sku: str) -> Optional[str]:
    """Map SKU naar gestandaardiseerde productnaam (gebaseerd op originele dictionaries.py)"""
    sku_mapping = {
        "8719326399355": "Citroen",
        "8719326399362": "Bloem", 
        "8719326399379": "Gember",
        "8719326399386": "Kombucha",
        "8719326399393": "Waterkefir",
        "8719327215111": "Starter Box",
        "8719327215128": "Frisdrank Mix",
        "8719327215135": "Mix Originals", 
        "8719327215180": "Probiotica"
    }
    return sku_mapping.get(sku)


def load_stock_to_database(conn: pyodbc.Connection, stock_data: List[Dict[str, Any]], stock_date: str) -> None:
    """Laad voorraadgegevens in de database
    
    Args:
        conn: Database connectie
        stock_data: List van voorraad items
        stock_date: Datum in YYYY-MM-DD formaat
    """
    if not stock_data:
        logging.warning("Geen voorraadgegevens om te laden")
        return
    
    logging.info(f"Start laden van {len(stock_data)} voorraad records voor datum {stock_date}")
    
    # Eerst bestaande records voor deze datum verwijderen
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM Stock WHERE StockDate = ?", stock_date)
        deleted_count = cursor.rowcount
        logging.info(f"{deleted_count} bestaande stock records verwijderd voor datum {stock_date}")
        conn.commit()
    
    # Nieuwe records invoegen
    insert_data = []
    skipped_count = 0
    
    for item in stock_data:
        try:
            # Extracteer basis product info
            sku = (item.get("Sku") or "").strip()
            if not sku:
                skipped_count += 1
                continue
                
            product_name = (item.get("Description") or "").strip() or None
            standardised_product = get_standardised_product_name(sku)
            product_id = item.get("ProductId")
            if product_id:
                try:
                    product_id = int(product_id)
                except (ValueError, TypeError):
                    product_id = None
            
            # Extracteer alle Monta stock velden uit de Stock sectie
            stock = item.get("Stock", {})
            stock_all = int(stock.get("StockAll", 0))
            stock_available = int(stock.get("StockAvailable", 0))
            stock_reserved = int(stock.get("StockReserved", 0))
            stock_in_transit = int(stock.get("StockInTransit", 0))
            stock_blocked = int(stock.get("StockBlocked", 0))
            stock_quarantaine = int(stock.get("StockQuarantaine", 0))
            stock_picking = int(stock.get("StockPicking", 0))
            stock_open = int(stock.get("StockOpen", 0))
            stock_in_warehouse = int(stock.get("StockInWarehouse", 0))
            stock_inbound_forecasted = int(stock.get("StockInboundForecasted", 0))
            stock_inbound_history = int(stock.get("StockInboundHistory", 0))
            stock_whole_saler = int(stock.get("StockWholeSaler", 0))
            
            insert_data.append((
                sku, product_name, standardised_product, product_id, stock_date,
                stock_all, stock_available, stock_reserved, stock_in_transit,
                stock_blocked, stock_quarantaine, stock_picking, stock_open,
                stock_in_warehouse, stock_inbound_forecasted, stock_inbound_history, stock_whole_saler
            ))
            
        except Exception as e:
            logging.warning(f"Fout bij verwerken stock item {item}: {e}")
            skipped_count += 1
            continue
    
    if insert_data:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO Stock (
                    ProductSKU, ProductName, StandardisedProduct, ProductID, StockDate,
                    StockAll, StockAvailable, StockReserved, StockInTransit,
                    StockBlocked, StockQuarantaine, StockPicking, StockOpen,
                    StockInWarehouse, StockInboundForecasted, StockInboundHistory, StockWholeSaler
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                insert_data
            )
            conn.commit()
            logging.info(f"{len(insert_data)} nieuwe stock records ingevoegd")
            
        if skipped_count > 0:
            logging.warning(f"{skipped_count} records overgeslagen wegens ontbrekende SKU of andere fouten")
    else:
        logging.warning("Geen geldige stock records om in te voegen")


def load_stock_for_date_range(start_date: str, end_date: str) -> None:
    """Laad voorraadgegevens voor een datumbereik
    
    Args:
        start_date: Start datum in YYYY-MM-DD formaat
        end_date: Eind datum in YYYY-MM-DD formaat
    """
    logging.info(f"Start laden voorraadgegevens van {start_date} tot {end_date}")
    
    # Configuratie ophalen
    db_config = get_config_from_env()
    monta_config = get_monta_config_from_env()
    
    # Verbindingen maken
    conn = connect_azuresql(db_config)
    monta_client = MontaClient(monta_config)
    
    try:
        # Voorraadgegevens ophalen van Monta
        stock_data = monta_client.get_stock_data(start_date, end_date)
        
        if not stock_data:
            logging.warning("Geen voorraadgegevens ontvangen van Monta API")
            return
        
        # Data laden voor elke dag in het bereik
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            load_stock_to_database(conn, stock_data, date_str)
            current_date += timedelta(days=1)
            
    except Exception as e:
        logging.error(f"Fout bij laden voorraadgegevens: {e}")
        raise
    finally:
        conn.close()


def load_stock_today() -> None:
    """Laad voorraadgegevens voor vandaag"""
    today = datetime.now().strftime("%Y-%m-%d")
    load_stock_for_date_range(today, today)


def load_stock_last_week() -> None:
    """Laad voorraadgegevens voor de afgelopen 7 dagen"""
    today = datetime.now()
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    load_stock_for_date_range(week_ago, today_str)


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    parser = argparse.ArgumentParser(description="Laad voorraadgegevens van Monta API")
    parser.add_argument("--start-date", help="Start datum (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Eind datum (YYYY-MM-DD)")
    parser.add_argument("--today", action="store_true", help="Laad alleen voor vandaag")
    parser.add_argument("--last-week", action="store_true", help="Laad voor afgelopen 7 dagen")
    
    args = parser.parse_args()
    
    try:
        if args.today:
            load_stock_today()
        elif args.last_week:
            load_stock_last_week()
        elif args.start_date and args.end_date:
            load_stock_for_date_range(args.start_date, args.end_date)
        elif args.start_date:
            # Als alleen start_date gegeven, gebruik vandaag als end_date
            today = datetime.now().strftime("%Y-%m-%d")
            load_stock_for_date_range(args.start_date, today)
        else:
            # Standaard: laad voor vandaag
            load_stock_today()
            
    except Exception as e:
        logging.error(f"Script gefaald: {e}")
        sys.exit(1)



