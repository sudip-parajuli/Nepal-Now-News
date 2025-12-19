import os
import pickle
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeUploader:
    def __init__(self, secrets_file='client_secrets.json', token_file='token.pickle'):
        self.secrets_file = secrets_file
        self.token_file = token_file
        self.youtube = self._get_authenticated_service()

    def _get_authenticated_service(self):
        creds = None
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.secrets_file):
                    print(f"Error: {self.secrets_file} not found. Please provide it for YouTube uploading.")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(self.secrets_file, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        return build('youtube', 'v3', credentials=creds)

    def upload_video(self, file_path, title, description, tags, category_id="25", privacy_status="public"):
        """
        Uploads a video to YouTube. Category 25 is 'News & Politics'.
        """
        if not self.youtube:
            print("YouTube service not initialized.")
            return

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacyStatus,
                'selfDeclaredMadeForKids': False
            }
        }

        media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
        request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")
        
        print(f"Video uploaded successfully! ID: {response['id']}")
        return response['id']

if __name__ == "__main__":
    pass
    # Test (requires client_secrets.json)
    # uploader = YouTubeUploader()
    # uploader.upload_video("test_video.mp4", "Test Breaking News", "Summary", ["news", "breaking"])
