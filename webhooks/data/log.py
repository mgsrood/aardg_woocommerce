from datetime import timedelta, datetime
import logging
import pyodbc
import time

class DatabaseHandler(logging.Handler):
    def __init__(self, conn_str, customer, source, script, script_id):
        super().__init__()
        self.conn_str = conn_str
        self.customer = customer
        self.source = source
        self.script = script
        self.script_id = script_id
        self.conn = None
        self.cursor = None
        self.connect_to_database()
        self.ensure_table_exists()

    def connect_to_database(self):
        try:
            # Gebruik autocommit zodat iedere execute meteen wordt doorgevoerd
            self.conn = pyodbc.connect(self.conn_str, autocommit=True)
            self.cursor = self.conn.cursor()
        except Exception as e:
            # Gebruik handleError om fouten netjes af te handelen zonder recursieve logging
            self.handleError(e)

    def ensure_table_exists(self):
        try:
            self.cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Logboek' AND xtype='U')
                CREATE TABLE Logboek (
                    ID INT IDENTITY PRIMARY KEY,
                    Niveau VARCHAR(50),
                    Bericht TEXT,
                    Datumtijd DATETIME,
                    Klant VARCHAR(100),
                    Bron VARCHAR(100),
                    Script VARCHAR(100),
                    Script_ID INT
                )
            ''')
        except Exception as e:
            self.handleError(e)

    def reconnect(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.connect_to_database()

    def emit(self, record):
        for attempt in range(2):
            try:
                if self.conn is None:
                    self.reconnect()
                # Format het bericht en verwijder de timestamp en level (zoals in jouw oorspronkelijke code)
                log_message = self.format(record)
                log_message = log_message.split('-')[-1].strip()
                created_at = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
                self.cursor.execute(
                    "INSERT INTO Logboek (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (record.levelname, log_message, created_at, self.customer, self.source, self.script, self.script_id)
                )
                # Als het invoegen succesvol is, stoppen we hier
                return
            except Exception as e:
                # Probeer een reconnect bij de eerste fout
                if attempt == 0:
                    self.reconnect()
                else:
                    # Als het na de reconnect nog niet lukt, roep de standaard foutafhandeling aan
                    self.handleError(record)
                    return

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception as e:
            self.handleError(e)
        super().close()


# Functie om logging op te zetten
def setup_logging(conn_str, klant, bron, script, script_id, log_file='app.log', log_level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # File handler voor lokale logbestanden
    file_handler = logging.FileHandler(log_file)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Database handler voor logging naar de database
    db_handler = DatabaseHandler(conn_str, klant, bron, script, script_id)
    db_handler.setFormatter(file_formatter)
    logger.addHandler(db_handler)

    logging.info("Logboek is geconfigureerd.")


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
