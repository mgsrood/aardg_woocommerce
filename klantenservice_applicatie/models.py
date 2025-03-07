from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_user_by_username(username):
        # Hier zou je normaal gesproken de database checken
        # Voor nu gebruiken we een dictionary met voorgedefinieerde gebruikers
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