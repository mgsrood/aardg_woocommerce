from g_modules.database import connect_to_database
from threading import Lock
import logging
import time

# Global counter en lock
_script_id_counter = 0
_script_id_lock = Lock()
_is_initialized = False

def _initialize_counter(greit_connection_string):
    """Initialiseert de counter met het hoogste Script ID uit de Logboek tabel"""
    global _script_id_counter, _is_initialized
    
    if _is_initialized:
        return

    with _script_id_lock:
        if _is_initialized:  # Double-check binnen de lock
            return
            
        try:
            database_conn = connect_to_database(greit_connection_string)
            if database_conn:
                cursor = database_conn.cursor()
                # Hoogste Script ID ophalen
                query = 'SELECT MAX(Script_ID) FROM Logboek'
                cursor.execute(query)
                highest_id = cursor.fetchone()[0]
                
                if highest_id:
                    _script_id_counter = highest_id
                    logging.info(f"Script ID counter geïnitialiseerd op {highest_id}")
                else:
                    _script_id_counter = 0
                    logging.info("Geen bestaande Script IDs gevonden, counter start bij 0")
                
                cursor.close()
                database_conn.close()
            else:
                logging.warning("Kon geen database verbinding maken voor Script ID initialisatie")
                _script_id_counter = 0
                
        except Exception as e:
            logging.error(f"Fout bij initialiseren Script ID counter: {e}")
            _script_id_counter = 0
        
        _is_initialized = True

def determine_script_id(greit_connection_string):
    """Genereert een uniek, oplopend Script ID op een thread-safe manier"""
    global _script_id_counter
    
    # Zorg dat de counter is geïnitialiseerd
    _initialize_counter(greit_connection_string)
    
    # Genereer nieuw ID
    with _script_id_lock:
        _script_id_counter += 1
        new_id = _script_id_counter
        logging.info(f"Nieuw ScriptID toegekend: {new_id}")
        return new_id