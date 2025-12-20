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
    if not os.path.exists('client_secrets.json'):
        print("Error: client_secrets.json not found in the root directory.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    credentials = flow.run_local_server(port=0)
    
    import pickle
    creds_data = pickle.dumps(credentials)
    token_base64 = base64.b64encode(creds_data).decode('utf-8')
    
    print("\n--- NEW YOUTUBE TOKEN ---")
    print("Copy the following string into your environment variable (e.g. YOUTUBE_TOKEN_SCIENCE_BASE64):")
    print("-" * 20)
    print(token_base64)
    print("-" * 20)

if __name__ == "__main__":
    main()
