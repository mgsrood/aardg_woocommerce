from modules.database import connect_to_database
from modules.log import log
import time

def fetch_script_id(greit_connection_string):
    database_conn = None
    try:
        database_conn = connect_to_database(greit_connection_string)
        if database_conn:
            cursor = database_conn.cursor()
            query = 'SELECT MAX(ScriptID) FROM Logging'
            cursor.execute(query)
            latest_script_id = cursor.fetchone()[0]
            if latest_script_id is not None:
                return latest_script_id + 1
            return 1  # Als er geen eerdere script_id's zijn
    except Exception as e:
        print(f"Error fetching script ID: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if database_conn:
            database_conn.close()
            
def set_script_id(greit_connection_string, klant, bron, actie_naam, script):
    start_time = time.time()
    script_id = fetch_script_id(greit_connection_string)
    log(greit_connection_string, klant, bron, actie_naam, script, script_id, tabel=None)
    
    return start_time, script_id