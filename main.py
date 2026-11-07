from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import hashlib
import uuid

app = FastAPI()

# ✅ Your files are in the SAME folder — this is correct
templates = Jinja2Templates(directory=".")

# Database connection
def get_db():
    conn = sqlite3.connect("jong_website.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Create table if not exists
def init_db():
    conn = sqlite3.connect("jong_website.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            bio TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Hash password
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Session storage
sessions = {}

# Get logged-in user
def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in sessions:
        raise HTTPException(status_code=401)
    conn = next(get_db())
    user = conn.execute("SELECT * FROM users WHERE id = ?", (sessions[session_id],)).fetchone()
    if not user:
        raise HTTPException(status_code=401)
    return user

# ========== ROUTES ==========

# Homepage
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Login page
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    conn = next(get_db())
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user or user["password"] != hash_password(password):
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "❌ Wrong email or password — try again"
        })

    # ✅ Create session — you are logged in!
    session_id = str(uuid.uuid4())
    sessions[session_id] = user["id"]
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie("session_id", session_id, max_age=86400)
    return resp

# Register page
@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register_submit(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    conn = next(get_db())

    # Check if email/username already used
    if conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone():
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "❌ Email already used"
        })
    if conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone():
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "❌ Username taken"
        })

    # ✅ Save to database
    user_id = str(uuid.uuid4())
    conn.execute('''
        INSERT INTO users (id, first_name, last_name, username, email, password)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, first_name, last_name, username, email, hash_password(password)))
    conn.commit()

    # Auto login
    session_id = str(uuid.uuid4())
    sessions[session_id] = user_id
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie("session_id", session_id, max_age=86400)
    return resp

# Dashboard — only for logged-in users
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

# Profile
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user = Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.post("/profile/update")
async def profile_update(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    username: str = Form(...),
    bio: str = Form(""),
    user = Depends(get_current_user)
):
    conn = next(get_db())
    conn.execute('''
        UPDATE users SET first_name=?, last_name=?, username=?, bio=? WHERE id=?
    ''', (first_name, last_name, username, bio, user["id"]))
    conn.commit()
    return RedirectResponse(url="/profile", status_code=302)

# Logout
@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in sessions:
        del sessions[session_id]
    resp = RedirectResponse(url="/")
    resp.delete_cookie("session_id")
    return resp

# Run server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
