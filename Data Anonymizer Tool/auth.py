# auth.py
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin

USER_DB_FILE = "users.json"

login_manager = LoginManager()
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id_, username, role="Analyst"):
        self.id = id_
        self.username = username
        self.role = role

# simple JSON-backed user store for demonstration
def _load_users():
    if not os.path.exists(USER_DB_FILE):
        return {}
    with open(USER_DB_FILE, "r") as f:
        return json.load(f)

def _save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f)

def ensure_default_users():
    users = _load_users()
    # Create an admin user if no users exist (change password immediately)
    if "admin" not in users:
        users["admin"] = {
            "password_hash": generate_password_hash("ChangeMe123!"),  # change this
            "role": "Admin"
        }
        _save_users(users)

def validate_login(username, password):
    users = _load_users()
    if username in users and check_password_hash(users[username]["password_hash"], password):
        return User(username, username, users[username].get("role", "Analyst"))
    return None

@login_manager.user_loader
def load_user(user_id):
    users = _load_users()
    if user_id in users:
        return User(user_id, user_id, users[user_id].get("role", "Analyst"))
    return None
