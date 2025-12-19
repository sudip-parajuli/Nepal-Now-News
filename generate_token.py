import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow

# The same scope as in youtube_uploader.py
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def generate():
    secrets_file = 'client_secrets.json'
    if not os.path.exists(secrets_file):
        if os.path.exists('client_secret.json'):
            secrets_file = 'client_secret.json'
        else:
            print(f"Error: {secrets_file} not found. Please download it from Google Cloud Console.")
            return

    # Load client secrets and run flow
    print("Authorization flow starting... Please log in via the browser.")
    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Serialize credentials to base64
    creds_data = pickle.dumps(creds)
    b64_token = base64.b64encode(creds_data).decode('utf-8')
    
    print("\n" + "="*50)
    print("YOUR YOUTUBE_TOKEN_BASE64Secret (Copy this entire string):")
    print("="*50)
    print(b64_token)
    print("="*50)
    print("\nCopy the string above and add it to your GitHub Secrets or .env file.")

if __name__ == "__main__":
    generate()
