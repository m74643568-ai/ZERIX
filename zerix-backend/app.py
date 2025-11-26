from flask import Flask, render_template, request, redirect, session, url_for

app = Flask(__name__)
app.secret_key = "zerix_secret_123"

# صفحة الهوم
@app.route("/")
def home():
    return "Zerix Home Page Works!"

# صفحة تسجيل الدخول
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # تسجيل دخول بسيط (هتتطور بعدين)
        if username == "test" and password == "123":
            session["user"] = username
            return redirect("/profile")

        return "Wrong username or password"

    return '''
        <form method="POST">
            <input name="username" placeholder="Username">
            <input name="password" placeholder="Password" type="password">
            <button type="submit">Login</button>
        </form>
    '''

# صفحة البروفايل
@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")
    return f"Welcome {session['user']}! This is your profile."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
