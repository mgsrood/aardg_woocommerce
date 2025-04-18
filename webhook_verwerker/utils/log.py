from datetime import timedelta, datetime
import logging
import pyodbc
import time
from flask import request
import sys

class DatabaseLogHandler(logging.Handler):
    """
    Logging handler die direct naar de database schrijft voor start, eind en error logs.
    """
    def __init__(self, conn_str, customer, source, script):
        super().__init__()
        self.conn_str = conn_str
        self.customer = customer
        self.source = source
        self.script = script

    def emit(self, record):
        # Alleen start, eind en error logs verwerken
        if not (record.levelno >= logging.ERROR or 
                'Script started' in record.msg or 
                'Script ended' in record.msg):
            return

        try:
            log_message = self.format(record)
            log_message = log_message.split('-')[-1].strip()
            created_at = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            
            # Haal script_id op uit de request context
            script_id = getattr(request, 'script_id', None)
            
            # Als er geen script_id is, gebruik dan een default waarde
            if script_id is None:
                script_id = 0  # Default waarde voor startup logs
                logging.debug("Geen script_id gevonden in request context, gebruik default waarde")

            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO Logboek 
                           (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (record.levelname, log_message, created_at, 
                         self.customer, self.source, self.script, script_id)
                    )
                    conn.commit()
        except Exception as e:
            print(f"Fout bij schrijven naar database: {e}")

def setup_logging(conn_str, klant, bron, script):
    """
    Configureer logging met database logging voor start, eind en errors,
    en terminal logging voor alle berichten tijdens het testen.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Maak en configureer de database handler
    db_handler = DatabaseLogHandler(conn_str, klant, bron, script)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                datefmt='%Y-%m-%d %H:%M:%S')
    db_handler.setFormatter(formatter)
    logger.addHandler(db_handler)

    # Voeg terminal logging toe voor testen
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return db_handler

def start_log():
    """Log de start van een script uitvoering"""
    start_time = time.time()
    current_time = datetime.now()
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Script started at {formatted_time}")
    return start_time

def end_log(start_time):
    """Log de eindtijd en duratie van een script uitvoering"""
    end_time = time.time()
    total_time = timedelta(seconds=(end_time - start_time))
    total_time_str = str(total_time).split('.')[0]
    logging.info(f"Script ended in {total_time_str}")
