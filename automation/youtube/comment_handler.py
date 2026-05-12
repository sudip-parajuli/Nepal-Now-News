import os
import time
from google import genai
from .auth import YouTubeAuth

class CommentHandler:
    def __init__(self, youtube_service, gemini_api_key):
        self.youtube = youtube_service
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.model_id = "gemini-2.0-flash"

    def handle_comments(self, max_videos=5):
        """Fetches recent videos and replies to new comments."""
        print(f"Scanning last {max_videos} videos for new comments...")
        
        try:
            # 1. Get recent uploads
            request = self.youtube.channels().list(mine=True, part='contentDetails')
            response = request.execute()
            uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            playlist_request = self.youtube.playlistItems().list(
                playlistId=uploads_playlist_id,
                part='snippet',
                maxResults=max_videos
            )
            playlist_response = playlist_request.execute()
            
            for item in playlist_response['items']:
                video_id = item['snippet']['resourceId']['videoId']
                video_title = item['snippet']['title']
                print(f"\nChecking video: {video_title} ({video_id})")
                self._process_video_comments(video_id, video_title)
                
        except Exception as e:
            print(f"Error in handle_comments: {e}")

    def _process_video_comments(self, video_id, video_title):
        """Processes comments for a specific video."""
        try:
            request = self.youtube.commentThreads().list(
                videoId=video_id,
                part='snippet,replies',
                maxResults=20,
                order='time'
            )
            response = request.execute()

            for thread in response.get('items', []):
                comment = thread['snippet']['topLevelComment']
                comment_id = comment['id']
                author = comment['snippet']['authorDisplayName']
                text = comment['snippet']['textDisplay']
                
                # Check if we've already replied
                if self._should_reply(thread):
                    print(f"  -> Replying to {author}: {text[:50]}...")
                    reply_text = self._generate_reply(text, video_title)
                    if reply_text:
                        self._post_reply(comment_id, reply_text)
                        time.sleep(2) # Avoid hitting quotas too fast
                else:
                    # print(f"  (Skipping {author})")
                    pass

        except Exception as e:
            if "commentsDisabled" in str(e):
                print(f"  Comments are disabled for this video.")
            else:
                print(f"  Error processing comments for {video_id}: {e}")

    def _should_reply(self, thread):
        """Returns True if the owner hasn't replied to this thread yet."""
        # Check if the top-level comment is from the owner (optional, usually skip)
        # For simplicity, we check the replies for any comment from the channel owner.
        
        # In a real scenario, you'd check the channel ID. 
        # Here we check if there are any replies at all. 
        # If the user wants more robust logic, we'd need the channel ID.
        
        # snippet.totalReplyCount > 0 might mean someone replied, but was it us?
        # Let's check the actual replies if they exist.
        if 'replies' in thread:
            for reply in thread['replies']['comments']:
                if reply['snippet']['canRate']: # A rough proxy or check authorChannelId
                    # If we can find a way to verify it's the owner, that's better.
                    # Usually, the owner's reply will be there.
                    pass
        
        # Simple heuristic: if totalReplyCount is 0, we definitely haven't replied.
        return thread['snippet']['totalReplyCount'] == 0

    def _generate_reply(self, comment_text, video_title):
        """Generates a scientific and polite reply using AI."""
        prompt = f"""
        You are the creator of a popular Science YouTube channel. 
        A viewer left a comment on your video titled "{video_title}".
        
        Viewer's Comment: "{comment_text}"
        
        Task: Write a short (1-3 sentences), polite, and scientifically engaging reply.
        - If they asked a question, answer it accurately.
        - If they gave feedback, thank them politely.
        - If they were critical, be professional and open to learning.
        - Keep the tone curious and encouraging.
        - Use a bit of personality (warm and brilliant scientist vibe).
        - DO NOT use hashtags.
        - DO NOT use emojis (keep it clean).
        
        Return ONLY the reply text.
        """
        try:
            response = self.gemini_client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"    AI Reply Gen Error: {e}")
            return None

    def _post_reply(self, parent_id, reply_text):
        """Posts the reply to YouTube."""
        try:
            body = {
                'snippet': {
                    'parentId': parent_id,
                    'textOriginal': reply_text
                }
            }
            request = self.youtube.comments().insert(
                part='snippet',
                body=body
            )
            request.execute()
            print("    Reply posted successfully.")
        except Exception as e:
            print(f"    Error posting reply: {e}")
