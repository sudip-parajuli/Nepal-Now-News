import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found in .env")
    exit(1)

print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents="Say hello in one word."
    )
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
