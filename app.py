import os
from datetime import datetime
import markdown
from werkzeug.utils import secure_filename
from flask import Flask, flash, redirect, render_template, request, session, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from markupsafe import Markup

from helpers import login_required, allowed_file, ai_summarize_file, db, UPLOAD_FOLDER, add_syllabus, get_user_syllabuses
from helpers import login_required, allowed_file, ai_analyze_file, ai_validate_syllabus, ai_generate_resources, UPLOAD_FOLDER, get_db, query_db, execute_db, init_db

# Initialize database if it doesn't exist
init_db()

app = Flask(__name__)

# Add markdown filter for Jinja templates
@app.template_filter('markdown')
def markdown_filter(text):
    return Markup(markdown.markdown(text, extensions=[
        'fenced_code',
        'tables',
        'nl2br',
        'sane_lists',
        'pymdownx.magiclink'
    ]))

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

Session(app)

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/result")
@login_required
def result():
    username = session.get("username")
    user_files = os.listdir(app.config['UPLOAD_FOLDER'])
    user_file = None
    
    for file in user_files:
        if file.startswith(f"{username}_"):
            user_file = os.path.join(app.config['UPLOAD_FOLDER'], file)
            break

    if not user_file:
        flash("No uploaded file found.", "danger")
        return redirect("/upload")

    summary = ai_analyze_file(user_file)
    resources = ai_generate_resources(user_file)
    
    # Clean up the file after both operations complete
    try:
        if os.path.exists(user_file):
            os.remove(user_file)
    except:
        pass
    
    return render_template("result.html", summary=summary, resources=resources)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash("No selected file", "danger")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = f"{session.get('username')}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Validate if file is a syllabus
            is_valid, message = ai_validate_syllabus(filepath)
            print(f"Syllabus validation: {is_valid}, {message}")
            if not is_valid:
                # Delete the invalid file
                if os.path.exists(filepath):
                    os.remove(filepath)
                flash(f"Invalid file: {message}. Please upload a course syllabus.", "danger")
                return redirect("/upload")
            
            flash("File uploaded successfully", "success")
            return redirect("/result")
        else:
            flash("File type not allowed", "danger")
            return redirect(request.url)
    
    return render_template("request.html")

@app.route("/classes")
@login_required
def classes():
    """Display the user's uploaded syllabuses dashboard"""
    user_id = session.get('user_id')
    user_syllabuses = get_user_syllabuses(user_id)
    return render_template("classes.html", syllabuses=user_syllabuses)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username:
            flash("Must provide username", "danger")
            return redirect("/login")
        if not password:
            flash("Must provide password", "danger")
            return redirect("/login")

        users = query_db("SELECT * FROM users WHERE username = ?", [username])

        if len(users) != 1 or not check_password_hash(dict(users[0])["hash"], password):
            flash("Invalid username and/or password", "danger")
            return redirect("/login")

        user = dict(users[0])
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect("/")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        
        if not username:
            flash("Must provide username", "danger")
            return redirect("/register")
        if not password:
            flash("Must provide password", "danger")
            return redirect("/register")
        if not confirmation:
            flash("Must provide password confirmation", "danger")
            return redirect("/register")
        if password != confirmation:
            flash("Passwords must match", "danger")
            return redirect("/register")

        users = query_db("SELECT * FROM users WHERE username = ?", [username])

        if users:
            flash("Username already taken", "danger")
            return redirect("/register")

        hash_pwd = generate_password_hash(password)
        execute_db('INSERT INTO users (username, hash) VALUES(?, ?)', [username, hash_pwd])
        
        users = query_db("SELECT * FROM users WHERE username = ?", [username])
        user = dict(users[0])
        session["user_id"] = user["id"]
        session["username"] = user["username"]

        return redirect("/")
    
    return render_template("register.html")

if __name__ == "__main__":
    app.run(debug=True)
