import pyodbc
import time
import logging

def get_and_use_next_script_id(connection_string, bron, script_naam):
    """
    Claimt een nieuw script_id door direct een log entry te maken.
    
    Args:
        connection_string: Database connectie string
        bron: De bron (bijv. 'WooCommerce')
        script_naam: Naam van het script (bijv. 'Abonnement Verwerking')
        
    Returns:
        Een nieuw uniek script ID
    """
    with pyodbc.connect(connection_string) as conn:
        with conn.cursor() as cur:
            # Lock nemen
            cur.execute("SELECT TOP 1 1 FROM [dbo].[Logboek] WITH (TABLOCKX)")
            
            try:
                # Hoogste ID ophalen
                cur.execute("""
                    SELECT ISNULL(MAX(Script_ID), 0)
                    FROM [dbo].[Logboek]
                    WHERE Script_ID IS NOT NULL
                """)
                hoogste_id = cur.fetchone()[0]
                volgend_id = hoogste_id + 1
                
                # Direct gebruiken in nieuwe log entry
                cur.execute("""
                    INSERT INTO [dbo].[Logboek] 
                    (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID)
                    VALUES 
                    ('INFO', 'Script gestart', GETDATE(), 'Aard''g', ?, ?, ?)
                """, (bron, script_naam, volgend_id))
                
                conn.commit()
                time.sleep(0.1)  # Kleine pauze
                
                return volgend_id
                
            except Exception as e:
                logging.error(f"Fout bij genereren script ID: {str(e)}")
                raise
            finally:
                conn.commit()  # Release the lock