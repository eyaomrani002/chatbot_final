import json
import os
from app.utils.logging import initialize_logging

logger = initialize_logging()

def init_json_db(json_path):
    """Initialize users.json if it doesn't exist."""
    if not os.path.exists(json_path):
        try:
            with open(json_path, 'w') as f:
                json.dump([], f)
            logger.info(f"Initialized JSON database at {json_path}")
        except Exception as e:
            logger.error(f"Error initializing JSON database: {e}")
            raise

def read_users_json(json_path):
    """Read all users from users.json."""
    try:
        with open(json_path, 'r') as f:
            users = json.load(f)
        return users
    except Exception as e:
        logger.error(f"Error reading users from {json_path}: {e}")
        return []

def append_user_json(json_path, user_data):
    """Append a new user to users.json."""
    try:
        users = read_users_json(json_path)
        users.append(user_data)
        with open(json_path, 'w') as f:
            json.dump(users, f, indent=2)
        logger.info(f"User {user_data['username']} appended to {json_path}")
    except Exception as e:
        logger.error(f"Error appending user to {json_path}: {e}")
        raise

def get_next_json_id(users):
    """Get the next available user ID for JSON."""
    if not users:
        return 1
    return max(user['id'] for user in users) + 1