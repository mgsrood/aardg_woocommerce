#!/usr/bin/env python3
"""
Database initialisatie script voor de klantenservice applicatie.
Dit script maakt de users.db database aan en voegt een standaard admin gebruiker toe.
"""

import sqlite3
import os
from werkzeug.security import generate_password_hash

def get_db_path():
    """Bepaal het pad naar de database."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'users.db')

def init_db():
    """Initialiseer de database met een admin gebruiker."""
    db_path = get_db_path()
    
    # Controleer of de database al bestaat
    db_exists = os.path.exists(db_path)
    
    # Maak verbinding met de database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Maak de users tabel aan als deze nog niet bestaat
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Voeg een admin gebruiker toe als de database nieuw is
    if not db_exists:
        admin_username = 'admin'
        admin_password = 'admin'  # In productie gebruik je een veilig wachtwoord!
        admin_password_hash = generate_password_hash(admin_password)
        
        try:
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (admin_username, admin_password_hash)
            )
            print(f"Admin gebruiker '{admin_username}' aangemaakt met wachtwoord '{admin_password}'")
        except sqlite3.IntegrityError:
            print(f"Admin gebruiker '{admin_username}' bestaat al")
    
    # Commit de wijzigingen en sluit de verbinding
    conn.commit()
    conn.close()
    
    print(f"Database geïnitialiseerd op: {db_path}")

if __name__ == '__main__':
    init_db()
    print("Database initialisatie voltooid.")
    print("Je kunt nu inloggen met gebruikersnaam 'admin' en wachtwoord 'admin'.")
    print("Gebruik manage_users.py om extra gebruikers toe te voegen of te beheren.") 