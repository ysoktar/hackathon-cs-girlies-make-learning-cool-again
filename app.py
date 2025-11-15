import os
from werkzeug.utils import secure_filename
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required, allowed_file, ai, db, UPLOAD_FOLDER

max_question_number = 30

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
# configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ensure upload folder exists (helpers already creates it, but keep safe)
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

Session(app)


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        # check file part
        if 'file' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(dest)
            flash("File uploaded successfully", "success")
            response = ai(file)
            return redirect("/upload")
        else:
            flash("File type not allowed", "danger")
            return redirect(request.url)
    else:
        return render_template("request.html")


@app.route("/")
def index():
    return render_template("index.html")


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
        user = db.execute('INSERT INTO users (username, hash) VALUES(?, ?)', request.form.get("username"), hash)

        user = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        session["user_id"] = user[0]["id"]
        session["username"] = user[0]["username"]

        return redirect("/")
    else:
        return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)
