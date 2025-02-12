from database import connect_to_database
import logging
import time

def fetch_current_script_id(cursor):
    # Voer de query uit om het hoogste ScriptID op te halen
    query = 'SELECT MAX(Script_ID) FROM Logboek'
    cursor.execute(query)
    
    # Verkrijg het resultaat
    highest_script_id = cursor.fetchone()[0]

    return highest_script_id

def determine_script_id(greit_connection_string):
    try:
        database_conn = connect_to_database(greit_connection_string)
    except Exception as e:
        logging.info(f"Verbinding met database mislukt, foutmelding: {e}")
    if database_conn:
        logging.info(f"Verbinding met database geslaagd")
        cursor = database_conn.cursor()
        latest_script_id = fetch_current_script_id(cursor)
        logging.info(f"ScriptID: {latest_script_id}")
        database_conn.close()

    if latest_script_id:
        script_id = latest_script_id + 1
    else:
        script_id = 1
        
    logging.info(f"ScriptID: {script_id}")
    
    return script_id