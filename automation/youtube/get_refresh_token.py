import os
import json
import base64
from google_auth_oauthlib.flow import InstalledAppFlow

# Instructions:
# 1. Place your client_secret.json in this directory.
# 2. Run: python automation/youtube/get_refresh_token.py
# 3. Authenticate with the SPECIFIC YouTube channel (Science channel).
# 4. Copy the output base64 string and add it to your environment variables.

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    if not os.path.exists('client_secret.json'):
        print("Error: client_secret.json not found in the root directory.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    
    token_data = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    token_json = json.dumps(token_data)
    token_base64 = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
    
    print("\n--- NEW YOUTUBE TOKEN ---")
    print("Copy the following string into your environment variable (e.g. YOUTUBE_TOKEN_SCIENCE_BASE64):")
    print("-" * 20)
    print(token_base64)
    print("-" * 20)

if __name__ == "__main__":
    main()
