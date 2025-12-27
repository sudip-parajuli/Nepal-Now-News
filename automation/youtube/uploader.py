from googleapiclient.http import MediaFileUpload
from .auth import YouTubeAuth

class YouTubeUploader:
    def __init__(self, youtube_service=None):
        self.youtube = youtube_service

    def upload_video(self, file_path, title, description, tags, category_id="25", privacy_status="public"):
        """
        Uploads a video to YouTube.
        """
        if not self.youtube:
            print("YouTube service not initialized.")
            return None

        # Sanitize description
        if description:
            # YouTube API errors on < and > in descriptions
            description = description.replace("<", "").replace(">", "")
            # Truncate if too long (5000 is limit, keep safety margin)
            if len(description) > 4900:
                description = description[:4900] + "..."

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status,
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
        
        print(f"Video uploaded successfully! ID: {response.get('id')}")
        return response.get('id')
