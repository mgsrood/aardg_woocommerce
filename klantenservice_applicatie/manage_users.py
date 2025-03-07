import sqlite3
import os
from werkzeug.security import generate_password_hash

def get_db_path():
    # Bepaal het pad naar de database
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, 'users.db')

def connect_db():
    return sqlite3.connect(get_db_path())

def create_table():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database tabel aangemaakt in {get_db_path()}")

def add_user(username, password):
    conn = connect_db()
    cursor = conn.cursor()
    password_hash = generate_password_hash(password)
    try:
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
        conn.commit()
        print(f"Gebruiker '{username}' succesvol toegevoegd.")
    except sqlite3.IntegrityError:
        print(f"Gebruiker '{username}' bestaat al.")
    finally:
        conn.close()

def remove_user(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE username = ?', (username,))
    if cursor.rowcount == 0:
        print(f"Gebruiker '{username}' niet gevonden.")
    else:
        conn.commit()
        print(f"Gebruiker '{username}' succesvol verwijderd.")
    conn.close()

def list_users():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users')
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print("Geen gebruikers gevonden.")
    else:
        print("\nGebruikers in de database:")
        print("ID\tGebruikersnaam")
        print("-" * 30)
        for user in users:
            print(f"{user[0]}\t{user[1]}")

def main():
    create_table()
    while True:
        print("\nGebruikersbeheer")
        print("-" * 30)
        print("1. Gebruiker toevoegen")
        print("2. Gebruiker verwijderen")
        print("3. Gebruikers weergeven")
        print("4. Afsluiten")
        
        choice = input("\nKies een optie (1-4): ").strip()
        
        if choice == '1':
            username = input("Voer de gebruikersnaam in: ").strip()
            password = input("Voer het wachtwoord in: ").strip()
            add_user(username, password)
        elif choice == '2':
            username = input("Voer de gebruikersnaam in: ").strip()
            remove_user(username)
        elif choice == '3':
            list_users()
        elif choice == '4':
            print("Programma wordt afgesloten.")
            break
        else:
            print("Ongeldige keuze. Probeer opnieuw.")

if __name__ == '__main__':
    main()