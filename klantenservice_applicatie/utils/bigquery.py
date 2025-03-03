from google.cloud import bigquery
import os
import sqlite3
import pandas as pd
from dotenv import load_dotenv
import json
import logging

# Configureer logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Laad environment variables
load_dotenv()

def get_bigquery_client():
    """
    Creëer een BigQuery client met de credentials uit de environment variables.
    """
    try:
        # Controleer of er een JSON key file is gespecificeerd
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not credentials_path:
            # Als er geen pad is opgegeven, probeer de credentials direct uit de environment variable te halen
            credentials_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            
            if credentials_json:
                # Schrijf de credentials naar een tijdelijk bestand
                temp_credentials_path = 'temp_credentials.json'
                with open(temp_credentials_path, 'w') as f:
                    f.write(credentials_json)
                
                # Stel het pad in naar de tijdelijke credentials
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_credentials_path
                
                logger.info("Credentials geladen uit environment variable")
            else:
                logger.error("Geen BigQuery credentials gevonden. Stel GOOGLE_APPLICATION_CREDENTIALS of GOOGLE_CREDENTIALS_JSON in.")
                return None
        
        # Maak de BigQuery client
        client = bigquery.Client()
        logger.info("BigQuery client succesvol aangemaakt")
        return client
    
    except Exception as e:
        logger.error(f"Fout bij het maken van BigQuery client: {str(e)}")
        return None

def execute_query(query):
    """
    Voer een query uit op BigQuery en retourneer de resultaten als een DataFrame.
    """
    client = get_bigquery_client()
    if not client:
        return None
    
    try:
        logger.info(f"Query uitvoeren: {query[:100]}...")
        query_job = client.query(query)
        results = query_job.result()
        
        # Converteer naar DataFrame
        df = results.to_dataframe()
        logger.info(f"Query succesvol uitgevoerd, {len(df)} rijen opgehaald")
        return df
    
    except Exception as e:
        logger.error(f"Fout bij het uitvoeren van query: {str(e)}")
        return None

def fetch_subscriptions():
    """
    Haal alle abonnementen op uit BigQuery.
    """
    # Pas deze query aan naar de juiste tabel en velden in BigQuery
    project_id = os.getenv('BIGQUERY_PROJECT_ID')
    dataset = os.getenv('BIGQUERY_DATASET')
    table = os.getenv('BIGQUERY_SUBSCRIPTIONS_TABLE')
    limit = int(os.getenv('BIGQUERY_QUERY_LIMIT', '1000'))
    
    logger.info(f"BigQuery configuratie: project_id={project_id}, dataset={dataset}, table={table}")
    
    query = """
    SELECT 
        subscription_id as id, 
        status, 
        customer_id, 
        billing_first_name, 
        billing_last_name, 
        billing_email, 
        CAST(NULL AS STRING) as billing_phone,
        billing_address_1,
        billing_address_2,
        billing_postcode,
        billing_city,
        billing_country,
        date_created,
        date_modified,
        next_payment_date,
        total,
        payment_method,
        payment_method_title,
        billing_period,
        billing_interval,
        start_date,
        CAST(NULL AS STRING) as trial_end_date,
        end_date,
        CAST(NULL AS STRING) as meta_data
    FROM 
        `{project_id}.{dataset}.{table}`
    ORDER BY 
        subscription_id DESC
    LIMIT 
        {limit}
    """.format(
        project_id=project_id,
        dataset=dataset,
        table=table,
        limit=limit
    )
    
    return execute_query(query)

def fetch_orders():
    """
    Haal alle orders op uit BigQuery.
    """
    # Pas deze query aan naar de juiste tabel en velden in BigQuery
    project_id = os.getenv('BIGQUERY_PROJECT_ID')
    dataset = os.getenv('BIGQUERY_DATASET')
    table = os.getenv('BIGQUERY_ORDERS_TABLE')
    limit = int(os.getenv('BIGQUERY_QUERY_LIMIT', '1000'))
    
    logger.info(f"BigQuery configuratie: project_id={project_id}, dataset={dataset}, table={table}")
    
    query = """
    SELECT 
        order_id as id, 
        status, 
        customer_id, 
        billing_first_name, 
        billing_last_name, 
        billing_email, 
        CAST(NULL AS STRING) as billing_phone,
        billing_address_1,
        billing_address_2,
        billing_postcode,
        billing_city,
        billing_country,
        date_created,
        date_modified,
        total,
        payment_method,
        payment_method_title,
        CAST(NULL AS STRING) as meta_data
    FROM 
        `{project_id}.{dataset}.{table}`
    ORDER BY 
        order_id DESC
    LIMIT 
        {limit}
    """.format(
        project_id=project_id,
        dataset=dataset,
        table=table,
        limit=limit
    )
    
    return execute_query(query)

def create_sqlite_db():
    """
    Maak een SQLite database aan en creëer de benodigde tabellen.
    """
    db_path = os.getenv('SQLITE_DB_PATH', 'klantenservice_applicatie/data/woocommerce.db')
    
    # Zorg ervoor dat de directory bestaat
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Maak tabellen aan
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY,
            status TEXT,
            customer_id INTEGER,
            billing_first_name TEXT,
            billing_last_name TEXT,
            billing_email TEXT,
            billing_phone TEXT,
            billing_address_1 TEXT,
            billing_address_2 TEXT,
            billing_postcode TEXT,
            billing_city TEXT,
            billing_country TEXT,
            date_created TEXT,
            date_modified TEXT,
            next_payment_date TEXT,
            total REAL,
            payment_method TEXT,
            payment_method_title TEXT,
            billing_period TEXT,
            billing_interval INTEGER,
            start_date TEXT,
            trial_end_date TEXT,
            end_date TEXT,
            meta_data TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            status TEXT,
            customer_id INTEGER,
            billing_first_name TEXT,
            billing_last_name TEXT,
            billing_email TEXT,
            billing_phone TEXT,
            billing_address_1 TEXT,
            billing_address_2 TEXT,
            billing_postcode TEXT,
            billing_city TEXT,
            billing_country TEXT,
            date_created TEXT,
            date_modified TEXT,
            total REAL,
            payment_method TEXT,
            payment_method_title TEXT,
            meta_data TEXT
        )
        ''')
        
        conn.commit()
        logger.info("SQLite database en tabellen succesvol aangemaakt")
        return conn
    
    except Exception as e:
        logger.error(f"Fout bij het aanmaken van SQLite database: {str(e)}")
        return None

def save_to_sqlite(df, table_name, conn=None):
    """
    Sla een DataFrame op in de SQLite database.
    """
    if df is None or df.empty:
        logger.warning(f"Geen data om op te slaan in tabel {table_name}")
        return False
    
    db_path = os.getenv('SQLITE_DB_PATH', 'klantenservice_applicatie/data/woocommerce.db')
    close_conn = False
    
    try:
        if conn is None:
            conn = sqlite3.connect(db_path)
            close_conn = True
        
        # Converteer meta_data kolom naar JSON string als deze bestaat
        if 'meta_data' in df.columns:
            df['meta_data'] = df['meta_data'].apply(lambda x: json.dumps(x) if x else None)
        
        # Sla op in SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        logger.info(f"{len(df)} rijen opgeslagen in tabel {table_name}")
        return True
    
    except Exception as e:
        logger.error(f"Fout bij het opslaan naar SQLite tabel {table_name}: {str(e)}")
        return False
    
    finally:
        if close_conn and conn:
            conn.close()

def sync_data_from_bigquery():
    """
    Synchroniseer alle data van BigQuery naar de lokale SQLite database.
    """
    logger.info("Start synchronisatie van BigQuery naar SQLite")
    
    # Maak de database aan
    conn = create_sqlite_db()
    if not conn:
        return False
    
    try:
        # Haal data op en sla op
        subscriptions_df = fetch_subscriptions()
        save_to_sqlite(subscriptions_df, 'subscriptions', conn)
        
        orders_df = fetch_orders()
        save_to_sqlite(orders_df, 'orders', conn)
        
        logger.info("Synchronisatie voltooid")
        return True
    
    except Exception as e:
        logger.error(f"Fout tijdens synchronisatie: {str(e)}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    # Test de functionaliteit
    sync_data_from_bigquery() 