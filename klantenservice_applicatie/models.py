from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_user_by_username(username):
        # Probeer eerst uit de database te halen
        try:
            # Pad naar de database
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')
            
            # Verbinding maken met de database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Gebruiker ophalen
            cursor.execute('SELECT id, username, password_hash FROM users WHERE username = ?', (username,))
            user_data = cursor.fetchone()
            
            # Verbinding sluiten
            conn.close()
            
            # Als gebruiker gevonden is, maak een User object
            if user_data:
                return User(
                    id=user_data[0],
                    username=user_data[1],
                    password_hash=user_data[2]
                )
        except Exception as e:
            print(f"Database error: {e}")
        
        # Fallback naar hardgecodeerde gebruikers als database niet beschikbaar is
        users = {
            'admin': {
                'id': 1,
                'username': 'admin',
                'password_hash': generate_password_hash('admin')  # In productie gebruik je een veilig wachtwoord!
            }
        }
        
        user_data = users.get(username)
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password_hash']
            )
        
        return None 