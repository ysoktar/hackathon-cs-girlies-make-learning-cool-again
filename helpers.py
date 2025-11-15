import os
from cs50 import SQL
from flask import redirect, session
from functools import wraps
from google import genai

# --- Configuration for File Uploads ---
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

# Check and create the folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
# --------------------------------------

genai.configure(api_key=os.getenv("GENAI_API_KEY"))
client = genai.Client()

db = SQL("sqlite:///users.db")

def login_required(f):
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    # Function to check if the file extension is allowed
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ai(file):
    # Function to interact with GenAI API
    response = client.chat.completions.create(
        model="gemini-1.5-pro",
        messages=[
            {"role": "user", "content": f"Process the uploaded file: {file.filename}"}
        ]
    )
    print(response.choices[0].message)
    return response