import os
from datetime import datetime
import markdown
from werkzeug.utils import secure_filename
from flask import Flask, flash, redirect, render_template, request, session, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from markupsafe import Markup

from helpers import (
    login_required, allowed_file, ai_analyze_file, ai_validate_syllabus, 
    ai_generate_resources, ai_generate_ics, UPLOAD_FOLDER, get_db, query_db, execute_db, 
    init_db, add_syllabus_result, get_user_results
)

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
    
    # Get course name from session (custom name or filename)
    course_name = session.get('course_name')
    if not course_name:
        original_filename = session.get('uploaded_filename', 'Unknown Course')
        course_name = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    
    # Get semester dates from session
    semester_start = session.get('semester_start_date')
    semester_end = session.get('semester_end_date')
    
    # Generate ICS file
    ics_content = None
    if semester_start and semester_end:
        print("Generating ICS calendar file...")
        ics_content = ai_generate_ics(user_file, course_name, semester_start, semester_end)
    else:
        print("Skipping ICS generation - semester dates not provided")
    
    # Save to database before deleting file
    result_id = add_syllabus_result(
        user_id=session.get('user_id'),
        name=course_name,
        summary=summary,
        resources=resources,
        semester_start_date=semester_start,
        semester_end_date=semester_end
    )
    
    # Update ICS in database if generated
    if ics_content and result_id:
        from helpers import execute_db
        execute_db('UPDATE results SET ics = ? WHERE id = ?', [ics_content, result_id])
        print(f"ICS file saved to database for result ID: {result_id}")
    
    # Clean up the file after both operations complete
    try:
        if os.path.exists(user_file):
            os.remove(user_file)
    except:
        pass
    
    # Clear the session data
    session.pop('uploaded_filename', None)
    session.pop('course_name', None)
    session.pop('semester_start_date', None)
    session.pop('semester_end_date', None)
    
    return render_template("result.html", 
                         summary=summary, 
                         resources=resources, 
                         course_name=course_name, 
                         semester_start=semester_start, 
                         semester_end=semester_end,
                         result_id=result_id,
                         has_ics=ics_content is not None)

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
            
            # Store original filename and custom course name in session
            session['uploaded_filename'] = file.filename
            
            # Get custom course name from form (optional)
            course_name = request.form.get('course_name', '').strip()
            if course_name:
                session['course_name'] = course_name
            
            # Get semester dates from form (optional)
            semester_start = request.form.get('semester_start_date')
            semester_end = request.form.get('semester_end_date')
            
            # Store in session if provided
            if semester_start:
                session['semester_start_date'] = semester_start
            if semester_end:
                session['semester_end_date'] = semester_end
            
            # Validate if file is a syllabus
            is_valid, message = ai_validate_syllabus(filepath)
            print(f"Syllabus validation: {is_valid}, {message}")
            if not is_valid:
                # Delete the invalid file
                if os.path.exists(filepath):
                    os.remove(filepath)
                session.pop('uploaded_filename', None)
                session.pop('course_name', None)
                session.pop('semester_start_date', None)
                session.pop('semester_end_date', None)
                flash(f"Invalid file: {message}. Please upload a course syllabus.", "danger")
                return redirect("/upload")
            
            flash("File uploaded successfully", "success")
            return redirect("/result")
        else:
            flash("File type not allowed", "danger")
            return redirect(request.url)
    
    # GET request - get most recent syllabus for default dates
    user_id = session.get('user_id')
    recent_results = get_user_results(user_id)
    
    default_start = None
    default_end = None
    
    if recent_results and len(recent_results) > 0:
        most_recent = recent_results[-1]
        default_start = most_recent.get('semester_start_date')
        default_end = most_recent.get('semester_end_date')
    
    return render_template("request.html", 
                         default_start=default_start, 
                         default_end=default_end)

@app.route("/classes")
@login_required
def classes():
    """Display the user's uploaded syllabuses dashboard"""
    user_id = session.get('user_id')
    user_syllabuses = get_user_results(user_id)
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

@app.route("/download/ics/<int:result_id>")
@login_required
def download_ics(result_id):
    """Download ICS calendar file for a specific result"""
    from flask import send_file
    import io
    
    user_id = session.get('user_id')
    
    # Get the specific result
    result = query_db('SELECT * FROM results WHERE id = ? AND user_id = ?', [result_id, user_id], one=True)
    
    if not result:
        flash("Class not found.", "danger")
        return redirect("/classes")
    
    result_dict = dict(result)
    ics_blob = result_dict.get('ics')
    
    if not ics_blob:
        flash("No calendar file available for this class.", "warning")
        return redirect(f"/class/{result_id}")
    
    # Create a filename based on course name
    course_name = result_dict.get('name', 'course')
    safe_filename = "".join(c for c in course_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{safe_filename}_calendar.ics"
    
    # Send the file
    return send_file(
        io.BytesIO(ics_blob),
        mimetype='text/calendar',
        as_attachment=True,
        download_name=filename
    )

@app.route("/class/<int:class_id>")
@login_required
def view_class(class_id):
    """View details of a specific class/syllabus"""
    user_id = session.get('user_id')
    
    # Get the specific result
    result = query_db('SELECT * FROM results WHERE id = ? AND user_id = ?', [class_id, user_id], one=True)
    
    if not result:
        flash("Class not found.", "danger")
        return redirect("/classes")
    
    result_dict = dict(result)
    has_ics = result_dict.get('ics') is not None
    
    return render_template("result.html", 
                         summary=result_dict['summary'], 
                         resources=result_dict['resources'],
                         course_name=result_dict['name'],
                         semester_start=result_dict.get('semester_start_date'),
                         semester_end=result_dict.get('semester_end_date'),
                         result_id=class_id,
                         has_ics=has_ics)

if __name__ == "__main__":
    app.run(debug=True)
