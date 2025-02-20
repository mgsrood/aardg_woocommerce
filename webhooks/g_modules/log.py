from datetime import datetime, timedelta
import threading
import logging
import pyodbc
import time
import os

class DatabaseHandler(logging.Handler):
    def __init__(self, conn_str, customer, source, script, script_id, fallback_file='fallback.log'):
        super().__init__()
        self.conn_str = conn_str
        self.customer = customer
        self.source = source
        self.script = script
        self.script_id = script_id
        self.fallback_file = fallback_file
        self.reconnecting = False

        # Probeer verbinding te maken met de database
        try:
            self.conn = pyodbc.connect(self.conn_str)
            self.cursor = self.conn.cursor()
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
            self.conn.commit()
        except Exception as e:
            print(f"Fout bij het verbinden met de database: {e}")
            self.conn = None
            self.cursor = None

        # Start een achtergrondthread om fallback logs periodiek te flushen
        self.flush_thread = threading.Thread(target=self._flush_fallback_logs, daemon=True)
        self.flush_thread.start()

    def emit(self, record):
        try:
            log_message = self.format(record)
            log_message = log_message.split('-')[-1].strip()
            created_at = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')

            if self.conn is None or self.cursor is None:
                # Als de database niet beschikbaar is, sla de log entry op in het fallback-bestand
                self._fallback_log(record.levelname, log_message, created_at)
                self.reconnect()  # Probeer de verbinding te herstellen
                return

            self.cursor.execute(
                "INSERT INTO Logboek (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (record.levelname, log_message, created_at, self.customer, self.source, self.script, self.script_id)
            )
            self.conn.commit()

        except pyodbc.OperationalError:
            print("Databaseverbinding weg. Fallback log wordt opgeslagen.")
            self._fallback_log(record.levelname, log_message, created_at)
            self.reconnect()

        except Exception as e:
            print(f"Fout bij het loggen naar de database: {e}")
            self._fallback_log(record.levelname, log_message, created_at)

    def _fallback_log(self, level, message, timestamp):
        """Schrijf de log entry naar een fallback-bestand."""
        try:
            with open(self.fallback_file, 'a') as f:
                f.write(f"{timestamp} - {level} - {message}\n")
        except Exception as e:
            print(f"Fout bij het schrijven naar fallback-bestand: {e}")

    def _flush_fallback_logs(self):
        """Achtergrondthread die periodiek controleert en opgeslagen logs naar de database verstuurt."""
        while True:
            time.sleep(30)  # Wacht 30 seconden tussen pogingen
            if self.conn is None or self.cursor is None:
                try:
                    self.reconnect()
                except Exception:
                    continue  # Als reconnect mislukt, probeer het later opnieuw

            if os.path.exists(self.fallback_file):
                try:
                    with open(self.fallback_file, 'r') as f:
                        lines = f.readlines()
                    if not lines:
                        continue

                    for line in lines:
                        try:
                            # Verwacht formaat: "YYYY-MM-DD HH:MM:SS - LEVEL - bericht"
                            timestamp, level, message = line.strip().split(' - ', 2)
                        except Exception:
                            continue
                        self.cursor.execute(
                            "INSERT INTO Logboek (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (level, message, timestamp, self.customer, self.source, self.script, self.script_id)
                        )
                    self.conn.commit()
                    # Leeg het fallback-bestand na succesvolle flush
                    open(self.fallback_file, 'w').close()
                    print("Fallback logs succesvol geflusht.")
                except Exception as e:
                    print(f"Flush fallback logs mislukt: {e}")
                    continue

    def reconnect(self):
        """Herstel de databaseverbinding met een retry-mechanisme."""
        self.reconnecting = True
        retries = 3
        for attempt in range(1, retries + 1):
            try:
                print(f"Probeer opnieuw verbinding te maken... (poging {attempt})")
                self.conn = pyodbc.connect(self.conn_str, timeout=10)
                self.cursor = self.conn.cursor()
                print("Databaseverbinding hersteld.")
                self.reconnecting = False
                return
            except Exception as e:
                print(f"Poging {attempt} mislukt: {e}")
                time.sleep(5)
        print("Kon geen verbinding maken na meerdere pogingen.")
        self.conn = None
        self.cursor = None
        self.reconnecting = False

    def close(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception as e:
            print(f"Fout bij het sluiten van de databaseverbinding: {e}")
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
    db_handler = DatabaseHandler(conn_str, klant, bron, script, script_id)
    db_handler.setFormatter(file_formatter)  # Gebruik dezelfde formatter voor de database
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
