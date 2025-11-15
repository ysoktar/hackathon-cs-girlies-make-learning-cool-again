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

api_key=os.getenv("GENAI_API_KEY")
try:
    # Initialize the Gemini Client
    # It will automatically look for the GEMINI_API_KEY environment variable.
    client = genai.Client(api_key=api_key)
    print("Gemini client initialized successfully.")
except Exception as e:
    print(f"Error initializing GenAI client. Ensure the SDK is installed and GEMINI_API_KEY is set. Error: {e}")
    client = None


db = SQL("sqlite:///users.db")

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

def ai(filepath):
    # Function to interact with GenAI API - upload file first
    uploaded_file = client.files.upload(file=filepath)
    
    # Generate content using the uploaded file
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=["Give me a summary of this file.", uploaded_file]
    )
    
    return response

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

    except APIError as e:
        return f"An API Error occurred during generation: {e}"
    except FileNotFoundError:
        return f"Error: File not found at path: {filepath}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    finally:
        # 3. Clean up the uploaded file resource
        if uploaded_file:
            print(f"\n[CLEANUP] Deleting uploaded file: {uploaded_file.name}")
            client.files.delete(name=uploaded_file.name)
            print("[CLEANUP] File deleted.")