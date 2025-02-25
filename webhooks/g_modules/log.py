from datetime import timedelta, datetime
import logging
import pyodbc
import time

class BufferedDatabaseHandler(logging.Handler):
    def __init__(self, conn_str, customer, source, script, script_id):
        """
        Logging handler die logs buffert en pas aan het einde alles in één keer naar de database schrijft.
        """
        super().__init__()
        self.conn_str = conn_str
        self.customer = customer
        self.source = source
        self.script = script
        self.script_id = script_id
        self.log_buffer = []  # Buffer om logs tijdelijk op te slaan

    def emit(self, record):
        """
        Voeg een logbericht toe aan de buffer.
        """
        log_message = self.format(record)
        log_message = log_message.split('-')[-1].strip()  # Optioneel: maak bericht schoner
        created_at = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

        log_entry = (record.levelname, log_message, created_at, self.customer, self.source, self.script, self.script_id)
        self.log_buffer.append(log_entry)

    def flush_logs(self):
        """
        Schrijf alle buffered logs in één keer naar de database.
        """
        if not self.log_buffer:
            return  # Niets om te flushen

        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.executemany(
                        "INSERT INTO Logboek (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        self.log_buffer
                    )
                    conn.commit()
            self.log_buffer.clear()  # Leeg de buffer na succesvolle insert
        except Exception as e:
            print(f"Fout bij flush_logs: {e}")

    def close(self):
        """
        Zorg ervoor dat alle logs worden geflushed voordat het script stopt.
        """
        self.flush_logs()
        super().close()


# Functie om logging op te zetten
def setup_logging(conn_str, klant, bron, script, script_id, log_file='app.log', log_level=logging.INFO):
    # Configureer de basis logging
    logger = logging.getLogger()  # Haal de root logger op
    logger.setLevel(log_level)

    # Maak de handlers
    file_handler = logging.FileHandler(log_file)

    # Formatteer de logberichten voor de file handler
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)

    # Voeg de handlers toe aan de logger
    logger.addHandler(file_handler)

    # Voeg de DatabaseHandler toe aan de logger
    db_handler = BufferedDatabaseHandler(conn_str, klant, bron, script, script_id)
    db_handler.setFormatter(file_formatter)  # Gebruik dezelfde formatter voor de database
    logger.addHandler(db_handler)

    logging.info("Logboek is geconfigureerd.")
    
    return db_handler

# Functie om de starttijd van het script te loggen
def start_log():
    start_time = time.time()
    current_time = datetime.now()
    formatted_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
    logging.info(f"Script started at {formatted_time}")
    
    return start_time

# Functie om de eindtijd van het script te loggen
def end_log(start_time):
    end_time = time.time()
    total_time = timedelta(seconds=(end_time - start_time))
    total_time_str = str(total_time).split('.')[0]
    logging.info(f"Script ended in {total_time_str}")
