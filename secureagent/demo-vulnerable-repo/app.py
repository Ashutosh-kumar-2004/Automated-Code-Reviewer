"""
Demo vulnerable Flask application containing intentional security flaws for SecureAgent testing:
1. SQL Injection (CWE-89)
2. Hardcoded API Secret (CWE-798)
3. Reflected Cross-Site Scripting (XSS) (CWE-79)
4. Insecure Deserialization (CWE-502)
"""
import sqlite3
import pickle
import base64
from flask import Flask, request, render_template_string

app = Flask(__name__)

# Hardcoded Secret (CWE-798)
DATABASE_API_KEY = "sk_live_9a8b7c6d5e4f3a2b1c0d_SUPER_SECRET_KEY"
JWT_SECRET_KEY = "hardcoded_secret_token_never_commit"

def get_db():
    conn = sqlite3.connect("users.db")
    return conn

@app.route("/")
def index():
    return "<h1>SecureAgent Demo Vulnerable Application</h1>"

@app.route("/user")
def get_user():
    # SQL Injection (CWE-89) - Concatenating untrusted user input directly into SQL query
    username = request.args.get("username", "")
    conn = get_db()
    cursor = conn.cursor()
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()
    return {"user": user}

@app.route("/greet")
def greet():
    # Reflected XSS (CWE-79) - Rendering unescaped user parameter in HTML template
    name = request.args.get("name", "Guest")
    template = f"<div>Hello {name}! Welcome to our site.</div>"
    return render_template_string(template)

@app.route("/load_session")
def load_session():
    # Insecure Deserialization (CWE-502) - Loading untrusted pickle object
    session_data = request.args.get("data")
    if session_data:
        raw_bytes = base64.b64decode(session_data)
        data = pickle.loads(raw_bytes)
        return {"session": str(data)}
    return {"session": None}

if __name__ == "__main__":
    app.run(port=5000)
