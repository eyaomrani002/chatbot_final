from flask import Flask, current_app
from flask_login import LoginManager
from threading import Lock
from .utils.logging import initialize_logging
from .utils.db import init_db
from .utils.json_db import init_json_db
import os
import sqlite3

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure random key
    app.config['UPLOAD_FOLDER'] = 'app/static/uploads'
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
    app.config['DB_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../users.db')
    app.config['JSON_DB_PATH'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../users.json')
    app.config['DATA_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')
    app.config['DATAFRAME'] = None
    app.config['VECTORIZER'] = None
    app.config['TFIDF_MATRIX'] = None
    app.config['DF_LOCK'] = Lock()

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    init_db()
    init_json_db(app.config['JSON_DB_PATH'])

    from .routes.api import api
    from .routes.auth import auth
    app.register_blueprint(api)
    app.register_blueprint(auth)

    logger = initialize_logging()
    logger.info("Flask app initialized successfully.")
    return app

@login_manager.user_loader
def load_user(user_id):
    from .models.user import User
    conn = sqlite3.connect(current_app.config['DB_PATH'])
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, password FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1], email=user_data[2], password=user_data[3])
    return None