from flask import Flask, request, redirect, render_template_string, session, url_for
import threading
import time
import requests
import sqlite3
import signal
import sys
from functools import wraps

app = Flask(__name__)
app.secret_key = "super_secret_key_for_session" # Required for sessions

DB_NAME = "sites.db"
PING_INTERVAL = 800  # 15 minutes

# Credentials
USERNAME = "kali"
PASSWORD = "a25"

# ---------- DATABASE ----------
def db():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sites(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE
        )
    """)
    conn.commit()
    conn.close()

def add_site(url):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO sites(url) VALUES(?)", (url,))
        conn.commit()
    except:
        pass
    conn.close()

def get_sites():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT url FROM sites")
    data = [r[0] for r in cur.fetchall()]
    conn.close()
    return data

def delete_site(url):
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM sites WHERE url=?", (url,))
    conn.commit()
    conn.close()

# ---------- AUTH DECORATOR ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---------- UI TEMPLATES ----------
LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login | Keep Alive</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: #1e1e1e; padding: 2rem; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 100%; max-width: 350px; text-align: center; }
        h2 { margin-bottom: 1.5rem; color: #00e676; }
        input { width: 100%; padding: 12px; margin: 10px 0; border-radius: 6px; border: 1px solid #333; background: #2c2c2c; color: white; box-sizing: border-box; }
        button { width: 100%; padding: 12px; border: none; border-radius: 6px; background: #00e676; color: #121212; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #00c853; }
        .error { color: #ff5252; font-size: 0.9rem; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>System Login</h2>
        {% if error %}<div class="error">{{error}}</div>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Access Dashboard</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard | Keep Alive</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 700px; margin: auto; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 30px; }
        h2 { color: #00e676; margin: 0; }
        .logout { color: #888; text-decoration: none; font-size: 0.9rem; border: 1px solid #333; padding: 5px 12px; border-radius: 4px; }
        .add-form { background: #1e1e1e; padding: 20px; border-radius: 8px; display: flex; gap: 10px; margin-bottom: 30px; }
        input { flex-grow: 1; background: #2c2c2c; border: 1px solid #444; color: white; padding: 10px; border-radius: 4px; }
        .btn-add { background: #00e676; color: black; border: none; padding: 10px 20px; border-radius: 4px; font-weight: bold; cursor: pointer; }
        .site-list { background: #1e1e1e; border-radius: 8px; overflow: hidden; list-style: none; padding: 0; }
        .site-item { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; border-bottom: 1px solid #333; }
        .site-item:last-child { border-bottom: none; }
        .url-text { color: #bbb; text-decoration: none; word-break: break-all; margin-right: 10px; }
        .btn-delete { color: #ff5252; text-decoration: none; font-weight: bold; font-size: 0.8rem; border: 1px solid #ff5252; padding: 4px 8px; border-radius: 4px; }
        .btn-delete:hover { background: #ff5252; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h2>Keep Alive Bot</h2>
            <a href="/logout" class="logout">Logout</a>
        </header>

        <form class="add-form" method="POST">
            <input name="url" placeholder="https://your-website.com" required>
            <button class="btn-add">Add URL</button>
        </form>

        <h3 style="color: #888;">Monitoring ({{ sites|length }})</h3>
        <ul class="site-list">
            {% for s in sites %}
            <li class="site-item">
                <span class="url-text">{{s}}</span>
                <a href="/delete?url={{s}}" class="btn-delete">REMOVE</a>
            </li>
            {% endfor %}
            {% if not sites %}
            <li class="site-item" style="color: #555; justify-content: center;">No sites added yet.</li>
            {% endif %}
        </ul>
    </div>
</body>
</html>
"""

# ---------- PINGER THREAD ----------
running = True

def pinger():
    headers = {"User-Agent": "Mozilla/5.0 AliveBot"}
    while running:
        sites = get_sites()
        for url in sites:
            try:
                r = requests.get(url, timeout=25, headers=headers)
                print(f"[PING] {url} -> {r.status_code}")
            except Exception as e:
                print(f"[ERROR] {url} -> {e}")
        time.sleep(PING_INTERVAL)

# ---------- ROUTES ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("home"))
        else:
            error = "Invalid Credentials"
    return render_template_string(LOGIN_HTML, error=error)

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    if request.method == "POST":
        url = request.form["url"].strip()
        if url.startswith("http"):
            add_site(url)
        return redirect("/")
    return render_template_string(DASHBOARD_HTML, sites=get_sites())

@app.route("/delete")
@login_required
def remove():
    url = request.args.get("url")
    if url:
        delete_site(url)
    return redirect("/")

# ---------- CLEAN EXIT ----------
def stop(sig, frame):
    global running
    running = False
    print("\nStopping server...")
    sys.exit(0)

signal.signal(signal.SIGINT, stop)

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    threading.Thread(target=pinger, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
