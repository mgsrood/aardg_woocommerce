from datetime import datetime, timedelta
import threading
import logging
import pyodbc
import time
import os
from typing import Optional, Any

# Constants
DEFAULT_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 5  # seconds
FLUSH_INTERVAL = 30  # seconds
DEFAULT_LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class DatabaseHandler(logging.Handler):
    """A logging handler that writes log records to a SQL Server database.
    
    Includes fallback logging to file when database connection is unavailable
    and automatic reconnection attempts.
    """
    
    def __init__(
        self, 
        conn_str: str,
        customer: str,
        source: str,
        script: str,
        script_id: int,
        fallback_file: str = 'fallback.log'
    ) -> None:
        super().__init__()
        self.conn_str: str = conn_str
        self.customer: str = customer
        self.source: str = source
        self.script: str = script
        self.script_id: int = script_id
        self.fallback_file: str = fallback_file
        self.reconnecting: bool = False
        self.conn: Optional[Any] = None
        self.cursor: Optional[Any] = None

        self._initialize_database()
        self._start_flush_thread()

    def _initialize_database(self) -> None:
        """Initialize database connection and create table if it doesn't exist."""
        try:
            self.conn = pyodbc.connect(self.conn_str)
            self.cursor = self.conn.cursor()
            self._create_log_table()
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            self.conn = None
            self.cursor = None

    def _create_log_table(self) -> None:
        """Create the logging table if it doesn't exist."""
        if not self.cursor:
            return

        create_table_sql = '''
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
        '''
        self.cursor.execute(create_table_sql)
        self.conn.commit()

    def _start_flush_thread(self) -> None:
        """Start background thread for flushing fallback logs."""
        self.flush_thread = threading.Thread(
            target=self._flush_fallback_logs,
            daemon=True,
            name="FallbackLogFlusher"
        )
        self.flush_thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record by writing it to the database or fallback file."""
        try:
            log_message = self.format(record).split('-')[-1].strip()
            created_at = datetime.fromtimestamp(record.created).strftime(DEFAULT_DATE_FORMAT)

            if not self._is_database_connected():
                self._handle_disconnected_state(record.levelname, log_message, created_at)
                return

            self._write_to_database(record.levelname, log_message, created_at)

        except Exception as e:
            logging.error(f"Error in emit: {e}")
            self._fallback_log(record.levelname, log_message, created_at)

    def _is_database_connected(self) -> bool:
        """Check if database connection is active."""
        return bool(self.conn and self.cursor)

    def _handle_disconnected_state(self, level: str, message: str, timestamp: str) -> None:
        """Handle logging when database connection is unavailable."""
        logging.warning("Database connection unavailable. Using fallback logging.")
        self._fallback_log(level, message, timestamp)
        if not self.reconnecting:
            self.reconnect()

    def _write_to_database(self, level: str, message: str, timestamp: str) -> None:
        """Write log entry to database."""
        try:
            self.cursor.execute(
                """INSERT INTO Logboek 
                   (Niveau, Bericht, Datumtijd, Klant, Bron, Script, Script_ID) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (level, message, timestamp, self.customer, self.source, 
                 self.script, self.script_id)
            )
            self.conn.commit()
        except pyodbc.Error as e:
            raise Exception(f"Database write failed: {e}")

    def _fallback_log(self, level: str, message: str, timestamp: str) -> None:
        """Write log entry to fallback file when database is unavailable."""
        try:
            with open(self.fallback_file, 'a', encoding='utf-8') as f:
                f.write(f"{timestamp} - {level} - {message}\n")
        except IOError as e:
            logging.error(f"Failed to write to fallback file: {e}")

    def _flush_fallback_logs(self) -> None:
        """Background thread that periodically flushes stored logs to database."""
        while True:
            time.sleep(FLUSH_INTERVAL)
            
            if not self._is_database_connected():
                if not self.reconnecting:
                    self.reconnect()
                continue

            if not os.path.exists(self.fallback_file):
                continue

            try:
                self._process_fallback_file()
            except Exception as e:
                logging.error(f"Failed to flush fallback logs: {e}")

    def _process_fallback_file(self) -> None:
        """Process and clear fallback log file."""
        with open(self.fallback_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return

        successful_lines = []
        for line in lines:
            try:
                timestamp, level, message = line.strip().split(' - ', 2)
                self._write_to_database(level, message, timestamp)
                successful_lines.append(line)
            except Exception as e:
                logging.error(f"Failed to process fallback log line: {e}")

        if successful_lines:
            # Remove processed lines from fallback file
            remaining_lines = [line for line in lines if line not in successful_lines]
            with open(self.fallback_file, 'w', encoding='utf-8') as f:
                f.writelines(remaining_lines)
            logging.info(f"Successfully flushed {len(successful_lines)} fallback log entries")

    def reconnect(self) -> None:
        """Attempt to restore database connection with retry mechanism."""
        if self.reconnecting:
            return

        self.reconnecting = True
        try:
            for attempt in range(1, DEFAULT_RECONNECT_ATTEMPTS + 1):
                try:
                    logging.info(f"Attempting database reconnection (attempt {attempt})")
                    self.conn = pyodbc.connect(self.conn_str, timeout=10)
                    self.cursor = self.conn.cursor()
                    logging.info("Database connection restored")
                    return
                except Exception as e:
                    if attempt < DEFAULT_RECONNECT_ATTEMPTS:
                        time.sleep(RECONNECT_DELAY)
                    else:
                        raise e
        except Exception as e:
            logging.error(f"Failed to reconnect after {DEFAULT_RECONNECT_ATTEMPTS} attempts: {e}")
            self.conn = None
            self.cursor = None
        finally:
            self.reconnecting = False

    def close(self) -> None:
        """Close database connections and perform cleanup."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except Exception as e:
            logging.error(f"Error closing database connection: {e}")
        super().close()

def setup_logging(
    conn_str: str,
    klant: str,
    bron: str,
    script: str,
    script_id: int,
    log_file: str = 'app.log',
    log_level: int = logging.INFO
) -> logging.Logger:
    """Configure logging with both file and database handlers.
    
    Args:
        conn_str: Database connection string
        klant: Customer identifier
        bron: Source identifier
        script: Script name
        script_id: Script identifier
        log_file: Path to log file
        log_level: Logging level
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Configure file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter(DEFAULT_LOG_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Configure database handler
    db_handler = DatabaseHandler(conn_str, klant, bron, script, script_id)
    db_handler.setFormatter(formatter)
    logger.addHandler(db_handler)

    logging.info("Logging system initialized")
    return logger

def start_log() -> float:
    """Log script start time and return start timestamp."""
    start_time = time.time()
    formatted_time = datetime.now().strftime(DEFAULT_DATE_FORMAT)
    logging.info(f"Script started at {formatted_time}")
    return start_time

def end_log(start_time: float) -> None:
    """Log script end time and duration.
    
    Args:
        start_time: Script start timestamp from start_log()
    """
    end_time = time.time()
    duration = timedelta(seconds=(end_time - start_time))
    duration_str = str(duration).split('.')[0]
    logging.info(f"Script ended. Total duration: {duration_str}")
