from flask import Flask, request, redirect, render_template_string
import threading
import time
import requests
import sqlite3
import signal
import sys

app = Flask(__name__)

DB_NAME = "sites.db"
PING_INTERVAL = 800  # 15 minutes


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


# ---------- HTML ----------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Keep Alive Dashboard</title>
</head>
<body style="font-family:Arial;text-align:center;margin-top:40px;">
<h2>Website Keep Alive</h2>

<form method="POST">
<input name="url" placeholder="https://example.com" required style="width:300px;height:30px;">
<button>Add</button>
</form>

<h3>Active Sites</h3>
<ul>
{% for s in sites %}
<li>
{{s}}
<a href="/delete?url={{s}}" style="color:red;">[remove]</a>
</li>
{% endfor %}
</ul>

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
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        url = request.form["url"].strip()
        if url.startswith("http"):
            add_site(url)
        return redirect("/")
    return render_template_string(HTML, sites=get_sites())


@app.route("/delete")
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
