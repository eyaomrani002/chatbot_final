from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from app.models.user import User
from app.utils.logging import initialize_logging
import sqlite3
import os
from app.utils.json_db import read_users_json, append_user_json, get_next_json_id

auth = Blueprint('auth', __name__)
logger = initialize_logging()

def get_db_connection():
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../users.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('auth.login'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, email, password FROM users WHERE username = ?', (username,))
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data and check_password_hash(user_data['password'], password):
                user = User(id=user_data['id'], username=user_data['username'], email=user_data['email'], password=user_data['password'])
                login_user(user)
                logger.info(f"User {username} logged in successfully.")
                return redirect(url_for('api.home'))
            else:
                flash('Invalid username or password.', 'error')
                logger.warning(f"Failed login attempt for username: {username}")
        
        except sqlite3.Error as e:
            logger.error(f"Database error during login: {e}")
            flash('An error occurred. Please try again.', 'error')
        
        return redirect(url_for('auth.login'))
    
    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not all([username, email, password]):
            flash('All fields are required.', 'error')
            return redirect(url_for('auth.register'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check for existing username in SQLite
            cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                conn.close()
                flash('Username already exists.', 'error')
                return redirect(url_for('auth.register'))
            
            # Check for existing email in SQLite
            cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                conn.close()
                flash('Email already registered.', 'error')
                return redirect(url_for('auth.register'))
            
            # Insert new user into SQLite
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                          (username, email, hashed_password))
            conn.commit()
            
            # Get the inserted user's ID
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            user_id = cursor.fetchone()['id']
            conn.close()
            
            # Append to users.json
            json_users = read_users_json(current_app.config['JSON_DB_PATH'])
            json_user_data = {
                'id': user_id,  # Use SQLite ID for consistency
                'username': username,
                'email': email,
                'password': hashed_password
            }
            append_user_json(current_app.config['JSON_DB_PATH'], json_user_data)
            
            logger.info(f"User {username} registered successfully in users.db and users.json.")
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        
        except sqlite3.Error as e:
            logger.error(f"Database error during registration: {e}")
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('auth.register'))
        except Exception as e:
            logger.error(f"Error appending to users.json: {e}")
            flash('An error occurred. Please try again.', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    logger.info("User logged out.")
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth.route('/users')
@login_required
def users():
    try:
        users = read_users_json(current_app.config['JSON_DB_PATH'])
        return render_template('users.html', users=users)
    except Exception as e:
        logger.error(f"Error fetching users from users.json: {e}")
        flash('An error occurred while fetching user data.', 'error')
        return redirect(url_for('api.home'))