from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, admin_required, get_questions, is_admin

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")


@app.route("/")
def index():
    return render_template("index.html", is_admin=is_admin())


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            flash("must provide username", "danger")
            return redirect("/login")
        elif not request.form.get("password"):
            flash("must provide password", "danger")
            return redirect("/login")

        user = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if len(user) != 1 or not check_password_hash(user[0]["hash"], request.form.get("password")):
            flash("Invalid username and/or password", "danger")
            return redirect("/login")

        session["user_id"] = user[0]["id"]
        session["username"] = user[0]["username"]

        return redirect("/")
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            flash("must provide username", "danger")
            return redirect("/register")
        elif not request.form.get("password"):
            flash("must provide password", "danger")
            return redirect("/register")
        elif not request.form.get("confirmation"):
            flash("must provide password confirmation", "danger")
            return redirect("/register")

        user = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if request.form.get("password") != request.form.get("confirmation"):
            flash("password and confirmation must be same", "danger")
            return redirect("/register")

        if user:
            flash("username taken", "danger")
            return redirect("/register")

        hash = generate_password_hash(request.form.get("password"))
        user = db.execute('INSERT INTO users (username, hash, role) VALUES(?, ?, "user")',
                          request.form.get("username"), hash)

        user = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = user[0]["id"]
        session["username"] = user[0]["username"]

        return redirect("/")
    else:
        return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)
