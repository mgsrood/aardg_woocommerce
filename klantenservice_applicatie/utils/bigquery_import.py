import os
import logging
from google.cloud import bigquery
from google.oauth2 import service_account
import sqlite3
from dotenv import load_dotenv

# Configureer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Laad environment variables
load_dotenv()

def get_db_connection():
    """
    Maak een verbinding met de SQLite database.
    """
    db_path = os.getenv('SQLITE_DB_PATH', 'klantenservice_applicatie/data/woocommerce.db')
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Hiermee kunnen we resultaten als dictionaries opvragen
        logger.debug(f"Verbinding gemaakt met database: {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Fout bij verbinden met database: {str(e)}")
        return None

def get_bigquery_client():
    """
    Maak een verbinding met BigQuery.
    """
    try:
        # Controleer of er een service account key file is opgegeven
        key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if key_path and os.path.exists(key_path):
            # Gebruik service account key file
            credentials = service_account.Credentials.from_service_account_file(
                key_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            client = bigquery.Client(credentials=credentials, project=credentials.project_id)
            logger.info(f"Verbinding gemaakt met BigQuery project: {credentials.project_id}")
        else:
            # Gebruik standaard authenticatie (ADC)
            client = bigquery.Client()
            logger.info(f"Verbinding gemaakt met BigQuery project: {client.project}")
        
        return client
    except Exception as e:
        logger.error(f"Fout bij verbinden met BigQuery: {str(e)}")
        import traceback
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return None

def create_order_margin_table():
    """
    Maak de order_margin_data tabel aan in de SQLite database.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        cursor = conn.cursor()
        
        # Controleer of de tabel al bestaat
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_margin_data'")
        if cursor.fetchone():
            logger.info("Tabel order_margin_data bestaat al")
            return {"success": True, "message": "Tabel bestaat al"}
        
        # Maak de tabel aan
        cursor.execute("""
            CREATE TABLE order_margin_data (
                order_id INTEGER PRIMARY KEY,
                cost REAL,
                revenue REAL,
                margin REAL,
                margin_percentage REAL,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        logger.info("Tabel order_margin_data aangemaakt")
        return {"success": True, "message": "Tabel aangemaakt"}
    
    except Exception as e:
        error_message = f"Fout bij aanmaken tabel: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def import_order_margin_data():
    """
    Haal order_margin_data op uit BigQuery en sla deze op in de SQLite database.
    """
    # Maak verbinding met BigQuery
    client = get_bigquery_client()
    if not client:
        return {"error": "Kan geen verbinding maken met BigQuery", "status": 500}
    
    # Maak verbinding met SQLite
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        # Maak de tabel aan als deze nog niet bestaat
        create_result = create_order_margin_table()
        if "error" in create_result:
            return create_result
        
        # Query om gegevens op te halen uit BigQuery
        query = """
            SELECT 
                order_id,
                cost,
                revenue,
                margin,
                margin_percentage,
                created_at,
                updated_at
            FROM 
                `order_data.order_margin_data`
            ORDER BY 
                order_id
        """
        
        logger.info("Ophalen van gegevens uit BigQuery...")
        query_job = client.query(query)
        rows = query_job.result()
        
        # Sla de gegevens op in SQLite
        cursor = conn.cursor()
        
        # Verwijder bestaande gegevens
        cursor.execute("DELETE FROM order_margin_data")
        
        # Voeg nieuwe gegevens toe
        count = 0
        for row in rows:
            cursor.execute("""
                INSERT INTO order_margin_data 
                (order_id, cost, revenue, margin, margin_percentage, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row.order_id,
                row.cost,
                row.revenue,
                row.margin,
                row.margin_percentage,
                row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else row.created_at,
                row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else row.updated_at
            ))
            count += 1
            
            # Commit elke 1000 rijen om geheugengebruik te beperken
            if count % 1000 == 0:
                conn.commit()
                logger.info(f"{count} rijen verwerkt...")
        
        # Commit resterende wijzigingen
        conn.commit()
        
        logger.info(f"Import voltooid: {count} rijen geïmporteerd")
        return {"success": True, "message": f"{count} rijen geïmporteerd"}
    
    except Exception as e:
        error_message = f"Fout bij importeren gegevens: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

def get_order_margin(order_id):
    """
    Haal de margegegevens op voor een specifieke order.
    """
    conn = get_db_connection()
    if not conn:
        return {"error": "Kan geen verbinding maken met de database", "status": 500}
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM order_margin_data WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"Geen margegegevens gevonden voor order ID: {order_id}")
            return {"error": f"Geen margegegevens gevonden voor order ID: {order_id}", "status": 404}
        
        margin_data = dict(row)
        logger.info(f"Margegegevens opgehaald voor order ID: {order_id}")
        return {"success": True, "data": margin_data}
    
    except Exception as e:
        error_message = f"Fout bij ophalen margegegevens: {str(e)}"
        logger.error(error_message)
        import traceback
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        return {"error": error_message, "status": 500}
    
    finally:
        conn.close()

if __name__ == "__main__":
    # Voer de import uit als dit script direct wordt uitgevoerd
    result = import_order_margin_data()
    print(result) 