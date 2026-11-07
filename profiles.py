from database import get_connection

def get_user_profile(user_id: int):
    if not user_id:
        return None
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, full_name, bio, avatar_url, created_at
        FROM users WHERE id = ?
    """, (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def update_profile(user_id: int, full_name: str = "", bio: str = ""):
    if not user_id:
        return False, "Invalid user"
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET full_name = ?, bio = ?
        WHERE id = ?
    """, (full_name.strip(), bio.strip(), user_id))
    conn.commit()
    conn.close()
    
    if cursor.rowcount > 0:
        return True, "Profile updated successfully"
    return False, "No changes made"
