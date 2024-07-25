from flask import Flask
import flask_monitoringdashboard as dashboard
from werkzeug.security import generate_password_hash

app = Flask(__name__)
dashboard.bind(app)

with app.app_context():
    from flask_monitoringdashboard.database import session_scope, User

    with session_scope() as db_session:
        admin = User(username='mgsrood', password=generate_password_hash('EqWzQhppoURsdtBYgRDXbthg'), admin=True)
        db_session.add(admin)
        db_session.commit()

print('Admin user created with username: mgsrood and password: EqWzQhppoURsdtBYgRDXbthg')
