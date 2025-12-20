# YouTube Authentication Guide

To enable automated uploads to YouTube Shorts from GitHub Actions, you need to generate a `YOUTUBE_TOKEN_BASE64` secret.

## 1. Get `client_secrets.json`
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., "Nepal Now News").
3. Search for **YouTube Data API v3** and click **Enable**.
4. Go to **Credentials** > **Create Credentials** > **OAuth client ID**.
5. Select **Desktop App** as the application type and name it.
6. Click **Create** and then download the JSON file. Rename it to `client_secrets.json`.

## 2. Generate `YOUTUBE_TOKEN_BASE64`
Since you don't want to install dependencies locally, you can use this simple script. It only requires `google-auth-oauthlib`.

### Install only required auth library:
```bash
pip install google-auth-oauthlib
```

### Run this script (`generate_token.py`):
```python
import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def generate():
    # Load client secrets
    flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Serialize credentials
    creds_data = pickle.dumps(creds)
    b64_token = base64.b64encode(creds_data).decode('utf-8')
    
    print("\n--- YOUR YOUTUBE_TOKEN_BASE64 ---")
    print(b64_token)
    print("--- COPY THE ABOVE STRING ---")

if __name__ == "__main__":
    generate()
```

## 3. Add to GitHub Secrets
1. Go to your GitHub repository: `sudip-parajuli/Nepal-Now-News`.
2. Go to **Settings** > **Secrets and variables** > **Actions**.
3. Create a **New repository secret**.

### For Multiple Channels:
If you have multiple YouTube channels (e.g., News and Science), name your secrets like this:
- **News Channel**: Name it `YOUTUBE_TOKEN_BASE64`
- **Science Channel**: Name it `YOUTUBE_TOKEN_SCIENCE`

This prevents naming conflicts and allows each pipeline to post to the correct channel.

## 4. Other Secrets
Ensure you have also added:
- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `TELEGRAM_API_ID` (if using telegram fetcher)
- `TELEGRAM_API_HASH` (if using telegram fetcher)
