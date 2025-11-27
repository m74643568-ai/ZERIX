# app.py
from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory
import sqlite3
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, "static", "uploads")
DB_PATH = os.path.join(APP_ROOT, "zerix.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = "zerix-secret-very-secret"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB limit

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ---- Helpers ----
def current_user():
    if "user_id" in session:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email FROM users WHERE id=?", (session["user_id"],))
        user = cur.fetchone()
        conn.close()
        return user
    return None

# ---- Routes ----
@app.route("/")
def index():
    user = current_user()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT posts.id, posts.text, posts.image, posts.created_at, users.username
        FROM posts JOIN users ON posts.user_id = users.id
        ORDER BY posts.created_at DESC
    """)
    posts = cur.fetchall()
    conn.close()
    return render_template("index.html", posts=posts, user=user)

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password")

        if not username or not email or not password:
            return "All fields are required", 400

        hashed = generate_password_hash(password)

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                        (username, email, hashed))
            conn.commit()
            conn.close()
            return redirect("/login")
        except sqlite3.IntegrityError:
            conn.close()
            return "Username or email already taken", 400

    return render_template("signup.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            return redirect("/")
        else:
            return "Invalid credentials", 401

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# Create Post (text + optional image)
@app.route("/post/create", methods=["GET", "POST"])
def create_post():
    user = current_user()
    if not user:
        return redirect("/login")

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        img = request.files.get("image")

        image_filename = None
        if img and img.filename != "":
            filename = secure_filename(img.filename)
            image_filename = f"{int(__import__('time').time())}_{filename}"
            img.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO posts (user_id, text, image) VALUES (?, ?, ?)", (user["id"], text, image_filename))
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("create_post.html", user=user)

# Serve uploaded images (Flask static can serve from /static by default,
# but include route if you want direct access)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# View single post (optional)
@app.route("/post/<int:post_id>")
def view_post(post_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""SELECT posts.*, users.username FROM posts JOIN users ON posts.user_id=users.id WHERE posts.id=?""", (post_id,))
    post = cur.fetchone()
    conn.close()
    if not post:
        return "Post not found", 404
    return render_template("post_view.html", post=post)

# Chat list / open chat with a user
@app.route("/chat", methods=["GET"])
def chat_list():
    user = current_user()
    if not user:
        return redirect("/login")
    # show simple list of other users
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE id != ?", (user["id"],))
    users = cur.fetchall()
    conn.close()
    return render_template("chat_list.html", users=users, user=user)

# Chat with specific user (simple message history)
@app.route("/chat/<int:other_id>", methods=["GET", "POST"])
def chat_with(other_id):
    user = current_user()
    if not user:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    # ensure other user exists
    cur.execute("SELECT id, username FROM users WHERE id=?", (other_id,))
    other = cur.fetchone()
    if not other:
        conn.close()
        return "User not found", 404

    if request.method == "POST":
        text = request.form.get("text", "").strip()
        if text:
            cur.execute("INSERT INTO messages (from_user, to_user, text) VALUES (?, ?, ?)",
                        (user["id"], other_id, text))
            conn.commit()

    # load last 200 messages between them
    cur.execute("""
      SELECT * FROM messages
      WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)
      ORDER BY created_at ASC
    """, (user["id"], other_id, other_id, user["id"]))
    messages = cur.fetchall()
    conn.close()
    return render_template("chat.html", messages=messages, other=other, user=user)

# API: send message (AJAX)
@app.route("/api/message/send", methods=["POST"])
def api_send_message():
    user = current_user()
    if not user:
        return {"error": "not authenticated"}, 401

    to_user = request.form.get("to_user")
    text = request.form.get("text", "").strip()
    if not to_user or not text:
        return {"error": "missing fields"}, 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages (from_user, to_user, text) VALUES (?, ?, ?)",
                (user["id"], to_user, text))
    conn.commit()
    conn.close()
    return {"ok": True}

# Profile
@app.route("/profile")
def profile():
    user = current_user()
    if not user:
        return redirect("/login")
    # show user's posts
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts WHERE user_id=? ORDER BY created_at DESC", (user["id"],))
    posts = cur.fetchall()
    conn.close()
    return render_template("profile.html", user=user, posts=posts)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
