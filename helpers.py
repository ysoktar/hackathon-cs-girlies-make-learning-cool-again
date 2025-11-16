import os
import sqlite3
from flask import redirect, session, g
from functools import wraps
from google import genai
from docx2pdf import convert

# --- Configuration for File Uploads ---
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

# Check and create the folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
# --------------------------------------

DATABASE = 'database.db'

def init_db():
    """Initialize database with schema if it doesn't exist"""
    if not os.path.exists(DATABASE):
        print("Database not found. Creating database...")
        conn = sqlite3.connect(DATABASE)
        
        # Read and execute schema
        schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql.txt')
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()
            print("Database created successfully!")
        else:
            print(f"Warning: Schema file not found at {schema_file}")
        
        conn.close()

def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        # Enable foreign key constraints
        db.execute("PRAGMA foreign_keys = ON")
    return db

def query_db(query, args=(), one=False):
    """Execute a query and return results"""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Execute a query that modifies the database"""
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    lastrowid = cur.lastrowid
    cur.close()
    return lastrowid

# Initialize the Gemini API client
api_key=os.getenv("GENAI_API_KEY")
try:
    client = genai.Client(api_key=api_key)
    print("Gemini client initialized successfully.")
except Exception as e:
    print(f"Error initializing GenAI client. Ensure the SDK is installed and GEMINI_API_KEY is set. Error: {e}")
    client = None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    # Function to check if the file extension is allowed
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ai_summarize_file(filepath):
    """
    Uploads a file and sends it to the Gemini API to request a summary.
    
    The uploaded file is managed by the API and needs to be deleted after use
    to avoid incurring storage charges or exceeding file limits.

    Args:
        filepath (str): The local path to the file to be uploaded.
    Returns:
        str: The generated text summary, or an error message.
    """
    if not client:
        return "API client not initialized. Cannot proceed."

    uploaded_file = None
    if filepath.lower().endswith('.docx') or filepath.lower().endswith('.doc') :
        # Convert DOCX to PDF
        pdf_filepath = filepath.rsplit('.', 1)[0] + '.pdf'
        convert(filepath, pdf_filepath)
        os.remove(filepath)  # Remove the original DOCX file after conversion
        filepath = pdf_filepath
    try:
        # 1. Upload the file
        print(f"\n[1/4] Uploading file: {os.path.basename(filepath)}...")
        uploaded_file = client.files.upload(file=filepath)
        print(f"[2/4] File uploaded successfully. URI: {uploaded_file.uri}")

        # 2. Generate content using the uploaded file
        print("[3/4] Requesting summary from model (gemini-2.5-flash)...")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=["Give me a concise summary of this file.", uploaded_file]
        )
        
        summary = response.text
        print("[4/4] Summary received.")
        return summary

    except FileNotFoundError:
        return f"Error: File not found at path: {filepath}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        # 3. Clean up the uploaded file resource
        if uploaded_file:
            print(f"\n[CLEANUP] Deleting uploaded file: {uploaded_file.name}")
            try:
                client.files.delete(name=uploaded_file.name)
                print("[CLEANUP] File deleted.")
            except Exception as cleanup_error:
                print(f"[CLEANUP] Failed to delete file: {cleanup_error}")
        if os.path.exists(filepath):
            os.remove(filepath)