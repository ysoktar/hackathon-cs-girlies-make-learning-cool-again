import os
from google import genai

# Load API key from environment variable
# For local testing you can set it here (do not commit secrets):
# os.environ['GEMINI_API_KEY'] = 'YOUR_API_KEY_HERE'
api_key = os.getenv('GEMINI_API_KEY')

print("Using API Key:", api_key)
# Initialize the client
client = genai.Client(api_key=api_key)

# Make API calls
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Tell me a joke about programming."
)
print(response.text)