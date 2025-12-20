import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeAuth:
    @staticmethod
    def get_service(token_b64=None, token_file='automation/storage/token.pickle', secrets_file='client_secrets.json'):
        creds = None
        
        # 1. Try environment variable
        if token_b64:
            try:
                creds_data = base64.b64decode(token_b64)
                creds = pickle.loads(creds_data)
                print("YouTube Auth: Loaded from environment.")
            except Exception as e:
                print(f"YouTube Auth Error: {e}")
        
        # 2. Try local token file
        if not creds and os.path.exists(token_file):
            try:
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
                    print("YouTube Auth: Loaded from local file.")
            except: pass
            
        # 3. Refresh or authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(secrets_file):
                    raise FileNotFoundError(f"Auth failed: {secrets_file} not found.")
                flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save token locally if not in GHA
            if not token_b64:
                os.makedirs(os.path.dirname(token_file), exist_ok=True)
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)

        return build('youtube', 'v3', credentials=creds)
