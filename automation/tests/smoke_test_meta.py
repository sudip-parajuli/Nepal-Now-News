import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add working directory to path
sys.path.append(os.getcwd())

from automation.meta.uploader import MetaUploader
from automation.meta.comment_handler import MetaCommentHandler

class TestMetaAutomation(unittest.TestCase):
    def setUp(self):
        # Set environment placeholders
        os.environ["META_ACCESS_TOKEN"] = "mock_token"
        os.environ["FACEBOOK_PAGE_ID"] = "mock_page_id"
        os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
        os.environ["GROQ_API_KEY"] = "mock_groq_key"

    @patch('requests.post')
    @patch('requests.get')
    def test_meta_uploader_translation_and_reconstruction(self, mock_get, mock_post):
        uploader = MetaUploader()
        
        # Mock SRT content
        original_srt = "1\n00:00:01,000 --> 00:00:04,500\nThis is a science fact.\n\n2\n00:00:04,600 --> 00:00:08,200\nThe universe is expanding."
        
        # Mock LLM translation response preserving numbering format
        mock_llm_response = "1: Esto es un hecho cientifico.\n2: El universo se esta expandiendo."
        uploader._call_llm_with_retry = MagicMock(return_value=mock_llm_response)
        
        translated_srt = uploader.translate_srt_content(original_srt, "Spanish")
        
        self.assertIn("Esto es un hecho cientifico.", translated_srt)
        self.assertIn("00:00:04,600 --> 00:00:08,200", translated_srt)
        self.assertIn("El universo se esta expandiendo.", translated_srt)

    @patch('requests.post')
    @patch('requests.get')
    def test_facebook_reels_upload_flow(self, mock_get, mock_post):
        uploader = MetaUploader()
        
        # Mocking initialization step
        mock_init_resp = MagicMock()
        mock_init_resp.json.return_value = {
            "video_id": "fb_reel_12345",
            "upload_url": "https://rupload.facebook.com/ig-api-upload/mock_url"
        }
        
        # Mocking binary chunk upload
        mock_chunk_resp = MagicMock()
        mock_chunk_resp.status_code = 200
        
        # Mocking finalization
        mock_finish_resp = MagicMock()
        mock_finish_resp.json.return_value = {
            "success": True,
            "video_id": "fb_reel_12345"
        }
        
        mock_post.side_effect = [mock_init_resp, mock_chunk_resp, mock_finish_resp]
        
        # Create a mock temporary video file
        temp_video = "automation/storage/mock_reel_temp.mp4"
        os.makedirs("automation/storage", exist_ok=True)
        with open(temp_video, "wb") as f:
            f.write(b"mock_video_bytes")
            
        reel_id = uploader._upload_facebook_reel(temp_video, "Check out this science Reel!")
        
        self.assertEqual(reel_id, "fb_reel_12345")
        
        # Cleanup
        if os.path.exists(temp_video):
            os.remove(temp_video)

    @patch('requests.post')
    @patch('requests.get')
    def test_comment_replies_scanning_and_handling(self, mock_get, mock_post):
        handler = MetaCommentHandler()
        
        # Mock FB Posts
        mock_posts_resp = MagicMock()
        mock_posts_resp.json.return_value = {
            "data": [
                {
                    "id": "post_111",
                    "message": "Expanding universe discussion",
                    "comments": {
                        "data": [
                            {
                                "id": "comment_abc",
                                "message": "Is space really infinite?",
                                "from": {"id": "viewer_user_id"}
                            }
                        ]
                    }
                }
            ]
        }
        
        # Mock FB Videos
        mock_videos_resp = MagicMock()
        mock_videos_resp.json.return_value = {
            "data": []
        }
        
        mock_get.side_effect = [mock_posts_resp, mock_videos_resp]
        
        # Mock LLM generation
        handler._generate_reply = MagicMock(return_value="Yes, current observations suggest space is flat and infinite.")
        
        # Mock posting reply response
        mock_post_resp = MagicMock()
        mock_post_resp.json.return_value = {"id": "reply_id_xyz"}
        mock_post.return_value = mock_post_resp
        
        # Execute comments scanning
        handler._handle_facebook_comments()
        
        # Assertions
        self.assertIn("comment_abc", handler.replied_comment_ids)
        handler._generate_reply.assert_called_once_with("Is space really infinite?", "Expanding universe discussion")

if __name__ == "__main__":
    unittest.main()
