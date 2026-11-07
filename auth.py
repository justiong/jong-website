import hashlib
import secrets
from database import get_connection

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{pw_hash}"

def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, pw_hash = stored_hash.split(":")
        computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return computed == pw_hash
    except Exception:
        return False

def register_user(username: str, email: str, password: str, full_name: str = ""):
    if not username or not email or not password:
        return False, "All required fields must be filled"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
            (username.strip(), email.strip(), hash_password(password), full_name.strip())
        )
        conn.commit()
        return True, "Registration successful! You can now log in"
    except sqlite3.IntegrityError:
        return False, "Username or email already exists"
    finally:
        conn.close()

def login_user(username_or_email: str, password: str):
    if not username_or_email or not password:
        return False, "Please fill in all fields"
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (username_or_email.strip(), username_or_email.strip())
    )
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return False, "User not found"
    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password"
    
    return True, dict(user)
