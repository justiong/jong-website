import secrets
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from database import init_db
from auth import register_user, login_user
from profiles import get_user_profile, update_profile

app = FastAPI()
init_db()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

sessions = {}

def get_current_user(request: Request):
    session_id = request.cookies.get("session_id")
    return sessions.get(session_id) if session_id else None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user_id": get_current_user(request)}
    )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error=None):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error": error}
    )

@app.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form("")
):
    ok, msg = register_user(username, email, password, full_name)
    if ok:
        return RedirectResponse("/login", status_code=303)
    return await register_page(request, error=msg)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error=None):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error}
    )

@app.post("/login")
async def login_submit(
    request: Request,
    username_or_email: str = Form(...),
    password: str = Form(...)
):
    ok, data = login_user(username_or_email, password)
    if ok:
        session_id = secrets.token_hex(16)
        sessions[session_id] = data["id"]
        resp = RedirectResponse("/profile", status_code=303)
        resp.set_cookie("session_id", session_id, httponly=True)
        return resp
    return await login_page(request, error=data)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "profile.html",
        {"request": request, "user": get_user_profile(user_id)}
    )

@app.post("/profile/update")
async def profile_update(
    request: Request,
    full_name: str = Form(""),
    bio: str = Form("")
):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse("/login")
    update_profile(user_id, full_name, bio)
    return RedirectResponse("/profile", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id:
        sessions.pop(session_id, None)
    resp = RedirectResponse("/")
    resp.delete_cookie("session_id")
    return resp

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
