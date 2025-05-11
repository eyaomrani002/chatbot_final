from flask import jsonify, current_app
from werkzeug.security import generate_password_hash
import logging
from . import db, User

logger = logging.getLogger(__name__)

def register_user(data):
    """Handle user registration."""
    try:
        # Validate input data
        if not data or 'fullName' not in data or 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Données manquantes'}), 400

        full_name = data['fullName'].strip()
        email = data['email'].strip().lower()
        password = data['password'].strip()

        # Server-side validation
        if not full_name or len(full_name) < 2:
            return jsonify({'error': 'Le nom complet doit contenir au moins 2 caractères'}), 400
        if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({'error': 'Email invalide'}), 400
        if len(password) < 8:
            return jsonify({'error': 'Le mot de passe doit contenir au moins 8 caractères'}), 400

        # Derive username from email (part before @)
        username = email.split('@')[0]

        # Check for existing user
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Cet email est déjà utilisé'}), 400
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Ce nom d’utilisateur est déjà pris'}), 400

        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        logger.info(f"Utilisateur inscrit avec succès: {username}")
        return jsonify({'success': True, 'message': 'Inscription réussie'}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l’inscription: {e}", exc_info=True)
        return jsonify({'error': 'Une erreur interne est survenue'}), 500