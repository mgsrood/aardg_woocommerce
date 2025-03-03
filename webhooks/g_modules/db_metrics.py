import pyodbc
from datetime import datetime
import json

def save_metrics_to_db(connection_string, metrics_data):
    """
    Slaat health check metrics op in de Azure SQL Database.
    
    Args:
        connection_string: Database connection string
        metrics_data: Dictionary met health check data
    """
    try:
        # Maak connectie
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()
        
        # Check of tabel bestaat, zo niet maak deze aan
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'health_metrics')
        CREATE TABLE health_metrics (
            ID INT IDENTITY(1,1) PRIMARY KEY,
            VM_naam VARCHAR(50) DEFAULT 'VM_Aardg',
            Datumtijd DATETIME,
            Status VARCHAR(50),
            Latency FLOAT,
            App_status VARCHAR(50),
            Redis_status VARCHAR(50),
            Redis_latency FLOAT,
            WooCommerce_status VARCHAR(50),
            WooCommerce_latency FLOAT,
            Succes INT,
            Foutmeldingen INT,
            Succes_ratio FLOAT,
            Geheugen_gebruik_Redis VARCHAR(50),
            CPU_percentage FLOAT,
            Geheugen_percentage FLOAT,
            Schijf_percentage FLOAT,
            Ruwe_data NVARCHAR(MAX),
            Aangemaakt DATETIME DEFAULT GETDATE()
        )
        """)
        
        # Haal relevante data uit de metrics
        now = datetime.now()
        components = metrics_data['components']
        metrics = metrics_data['metrics']
        cache_stats = metrics['cache']['global']
        system_stats = metrics['system']
        
        # Voeg record toe
        cursor.execute("""
        INSERT INTO health_metrics (
            Datumtijd,
            Status,
            Latency,
            App_status,
            Redis_status,
            Redis_latency,
            WooCommerce_status,
            WooCommerce_latency,
            Succes,
            Foutmeldingen,
            Succes_ratio,
            Geheugen_gebruik_Redis,
            CPU_percentage,
            Geheugen_percentage,
            Schijf_percentage,
            Ruwe_data
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            metrics_data['status'],
            metrics_data['latency_ms'],
            components['app']['status'],
            components['redis']['status'],
            components['redis'].get('latency_ms', 0),
            components['woocommerce']['status'],
            components['woocommerce'].get('latency_ms', 0),
            cache_stats['hits'],
            cache_stats['misses'],
            cache_stats['hit_rate'],
            metrics['redis_memory']['used_memory_human'],
            system_stats['cpu']['system_percent'],
            system_stats['memory']['system']['percent'],
            system_stats['disk']['percent'],
            json.dumps(metrics_data)
        ))
        
        # Commit de transactie
        conn.commit()
        
    except Exception as e:
        print(f"Error saving metrics to database: {str(e)}")
        raise
    
    finally:
        if 'conn' in locals():
            conn.close() 