import os
import time
import random
import re
import requests
from google import genai
from typing import List, Dict

class MetaUploader:
    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID")
        self.api_version = "v19.0"
        
        # Load API keys for translation rotation
        self.gemini_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY2"),
            os.getenv("GEMINI_API_KEY3")
        ]
        self.gemini_keys = [k for k in self.gemini_keys if k]
        self.gemini_clients = [genai.Client(api_key=k) for k in self.gemini_keys]
        self.model_id = "gemini-2.0-flash"
        
        self.groq_api_keys = [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY2"),
            os.getenv("GROQ_API_KEY3")
        ]
        self.groq_api_keys = [k for k in self.groq_api_keys if k]
        self.groq_clients = []
        if self.groq_api_keys:
            try:
                from groq import Groq
                self.groq_clients = [Groq(api_key=k) for k in self.groq_api_keys]
            except ImportError:
                pass

    def _call_llm_with_retry(self, prompt: str, max_retries: int = 5) -> str:
        """Call LLM with full fallback and rotation for translation tasks."""
        if not self.gemini_clients:
            print("WARNING: No Gemini clients available for translation. Trying Groq...")
            
        for client_idx, client in enumerate(self.gemini_clients):
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=self.model_id,
                        contents=prompt
                    )
                    return response.text.strip()
                except Exception as e:
                    err_msg = str(e).lower()
                    if "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg:
                        print(f"Gemini translation key {client_idx+1} quota exceeded. Trying next key...")
                        break
                    if attempt < max_retries - 1:
                        time.sleep(2 + random.uniform(0, 1))
                    else:
                        break
                        
        if self.groq_clients:
            for client_idx, groq_client in enumerate(self.groq_clients):
                for attempt in range(max_retries):
                    try:
                        chat_completion = groq_client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        )
                        result = chat_completion.choices[0].message.content.strip()
                        if result:
                            return result
                    except Exception as groq_err:
                        err_msg = str(groq_err).lower()
                        if "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg:
                            break
                        if attempt < max_retries - 1:
                            time.sleep((2 ** attempt) + 1)
        return ""

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text to the target language using rotating LLM."""
        prompt = f"""
        Translate the following text into {target_lang}.
        Maintain the exact same structure, timing elements, brackets, or numbers.
        If the text contains subtitle indexes or time codes, do not modify them.
        Provide ONLY the translated text without any explanations.
        
        Text to translate:
        "{text}"
        """
        return self._call_llm_with_retry(prompt)

    def translate_srt_content(self, srt_content: str, target_lang: str) -> str:
        """Parses SRT blocks, translates subtitle texts in batch to preserve context, and reconstructs SRT."""
        # Standardize newlines and split into blocks
        blocks = srt_content.replace('\r\n', '\n').strip().split('\n\n')
        parsed_blocks = []
        
        for block in blocks:
            lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
            if len(lines) >= 3:
                idx = lines[0]
                time_code = lines[1]
                text = " ".join(lines[2:])
                parsed_blocks.append({
                    "idx": idx,
                    "time_code": time_code,
                    "text": text
                })
                
        if not parsed_blocks:
            return ""
            
        # Collect sentences
        sentences = []
        for block in parsed_blocks:
            sentences.append(f"{block['idx']}: {block['text']}")
            
        batch_prompt = f"""
        Translate the following numbered sentences from a science documentary script into {target_lang}.
        Maintain the exact sentence numbers (e.g., "1: ...", "2: ...") and order.
        Return ONLY the translated list. Do not add any introduction or signature.
        
        Sentences:
        {chr(10).join(sentences)}
        """
        translated_batch = self._call_llm_with_retry(batch_prompt)
        
        # Parse translated sentences back
        translated_map = {}
        for line in translated_batch.split('\n'):
            line = line.strip()
            item_match = re.match(r'^(\d+)[\:\.]\s*(.*)$', line)
            if item_match:
                item_idx = item_match.group(1)
                val = item_match.group(2).strip()
                translated_map[item_idx] = val
                
        # Reconstruct SRT
        reconstructed = []
        for block in parsed_blocks:
            translated_text = translated_map.get(block['idx'], block['text'])
            reconstructed.append(f"{block['idx']}\n{block['time_code']}\n{translated_text}\n")
            
        return "\n".join(reconstructed)

    def upload_video(self, video_path: str, title: str, description: str, tags: List[str] = None) -> str:
        """Main method to upload a video/reel to Facebook and cross-post to Instagram."""
        if not self.access_token or not self.page_id:
            print("Meta posting credentials missing. Skipping Meta upload.")
            return None

        # Detect aspect ratio to classify if it is a Reel
        is_reel = True
        try:
            # Simple duration/dimensions classifier if possible, otherwise check title/tags
            if tags and "shorts" not in tags and "Shorts" not in title:
                is_reel = False
        except Exception:
            pass

        print(f"Meta Uploading: {title} (Is Reel: {is_reel})")
        fb_video_id = None
        if is_reel:
            fb_video_id = self._upload_facebook_reel(video_path, description)
        else:
            fb_video_id = self._upload_facebook_video(video_path, title, description)

        if not fb_video_id:
            print("Facebook Page upload failed. Cannot cross-post to Instagram.")
            return None

        print(f"Facebook Video published successfully! ID: {fb_video_id}")

        # Post captions to Facebook video if SRT file is available
        # In our pipeline, long-form SRT is saved at "automation/storage/science_long.srt"
        # and shorts don't have standard separate SRT files, but we check if one exists
        srt_path = "automation/storage/science_long.srt" if not is_reel else "automation/storage/science_shorts.srt"
        if os.path.exists(srt_path):
            self.upload_facebook_captions(fb_video_id, srt_path)

        # Cross-post to Instagram Business account if linked
        self._publish_to_instagram(fb_video_id, description)
        return fb_video_id

    def _upload_facebook_reel(self, video_path: str, description: str) -> str:
        """Uploads a Facebook Reel using the 3-step Resumable Upload API."""
        try:
            # Step 1: Start Upload Session
            init_url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}/video_reels"
            params = {
                "upload_phase": "start",
                "access_token": self.access_token
            }
            res = requests.post(init_url, params=params)
            res_data = res.json()
            if "video_id" not in res_data:
                print(f"Facebook Reels initialization failed: {res.text}")
                if "error" in res_data:
                    err_msg = res_data["error"].get("message", "")
                    if "pages_manage_posts" in err_msg or "permission" in err_msg.lower() or "OAuthException" in res_data["error"].get("type", ""):
                        print("\n" + "!" * 80)
                        print("CRITICAL: Meta Access Token lacks required permissions (e.g. pages_manage_posts).")
                        print("ACTION REQUIRED TO RESOLVE:")
                        print("1. Go to your Meta Developer App -> Graph API Explorer.")
                        print("2. Ensure your token has 'pages_manage_posts', 'pages_read_engagement', and 'pages_show_list'.")
                        print("3. IMPORTANT: Make sure you use a PAGE Access Token (obtained via GET /me/accounts),")
                        print("   NOT a USER Access Token.")
                        print("4. Update your META_ACCESS_TOKEN GitHub Secret with the new Page Access Token.")
                        print("!" * 80 + "\n")
                return None
                
            video_id = res_data["video_id"]
            upload_url = res_data["upload_url"]

            # Step 2: Upload Binary Chunks to rupload.facebook.com
            file_size = os.path.getsize(video_path)
            with open(video_path, "rb") as f:
                video_data = f.read()

            headers = {
                "Authorization": f"OAuth {self.access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }
            upload_res = requests.post(upload_url, data=video_data, headers=headers)
            if upload_res.status_code != 200:
                print(f"Facebook Reels chunk upload failed: {upload_res.text}")
                return None

            # Step 3: Finish and Publish Reel
            publish_params = {
                "video_id": video_id,
                "upload_phase": "finish",
                "video_state": "PUBLISHED",
                "description": description,
                "access_token": self.access_token
            }
            finish_res = requests.post(init_url, data=publish_params)
            finish_data = finish_res.json()
            if finish_data.get("success") or "video_id" in finish_data:
                return video_id
            print(f"Facebook Reels finalize failed: {finish_res.text}")
            return None
        except Exception as e:
            print(f"Error in _upload_facebook_reel: {e}")
            return None

    def _upload_facebook_video(self, video_path: str, title: str, description: str) -> str:
        """Uploads standard long-form video using simple multipart upload."""
        try:
            url = f"https://graph-video.facebook.com/{self.api_version}/{self.page_id}/videos"
            payload = {
                "title": title,
                "description": description,
                "access_token": self.access_token
            }
            with open(video_path, "rb") as f:
                files = {
                    "source": f
                }
                res = requests.post(url, data=payload, files=files)
            
            res_data = res.json()
            if "id" in res_data:
                return res_data["id"]
            print(f"Facebook Video upload failed: {res.text}")
            if "error" in res_data:
                err_msg = res_data["error"].get("message", "")
                if "pages_manage_posts" in err_msg or "permission" in err_msg.lower() or "OAuthException" in res_data["error"].get("type", ""):
                    print("\n" + "!" * 80)
                    print("CRITICAL: Meta Access Token lacks required permissions (e.g. pages_manage_posts).")
                    print("ACTION REQUIRED TO RESOLVE:")
                    print("1. Go to your Meta Developer App -> Graph API Explorer.")
                    print("2. Ensure your token has 'pages_manage_posts', 'pages_read_engagement', and 'pages_show_list'.")
                    print("3. IMPORTANT: Make sure you use a PAGE Access Token (obtained via GET /me/accounts),")
                    print("   NOT a USER Access Token.")
                    print("4. Update your META_ACCESS_TOKEN GitHub Secret with the new Page Access Token.")
                    print("!" * 80 + "\n")
            return None
        except Exception as e:
            print(f"Error in _upload_facebook_video: {e}")
            return None

    def upload_facebook_captions(self, fb_video_id: str, srt_path: str):
        """Translates the SRT file to multiple languages and uploads them all as subtitles."""
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                original_srt = f.read()

            languages = [
                ("Spanish", "es_LA"),
                ("French", "fr_FR"),
                ("German", "de_DE"),
                ("Portuguese", "pt_BR"),
                ("Hindi", "hi_IN")
            ]

            # 1. Upload English Captions first
            print("Uploading English captions...")
            self._upload_single_caption(fb_video_id, original_srt, "en_US", is_default=True)

            # 2. Translate and Upload other major languages
            for lang_name, locale in languages:
                print(f"Translating captions to {lang_name} ({locale})...")
                translated_srt = self.translate_srt_content(original_srt, lang_name)
                if translated_srt:
                    print(f"Uploading {lang_name} captions...")
                    self._upload_single_caption(fb_video_id, translated_srt, locale, is_default=False)
                else:
                    print(f"Failed to translate captions to {lang_name}")
        except Exception as e:
            print(f"Error in upload_facebook_captions: {e}")

    def _upload_single_caption(self, fb_video_id: str, srt_content: str, locale: str, is_default: bool = False):
        """Posts a single locale caption SRT file to the Facebook video captions endpoint."""
        try:
            url = f"https://graph-video.facebook.com/{self.api_version}/{fb_video_id}/captions"
            payload = {
                "access_token": self.access_token,
                "default_locale": locale if is_default else ""
            }
            # The files key name must match Facebook specification, filename should incorporate the locale
            files = {
                "captions_file": (f"captions.{locale}.srt", srt_content.encode("utf-8"), "application/x-subrip")
            }
            res = requests.post(url, data=payload, files=files)
            if res.json().get("success"):
                print(f"Successfully uploaded {locale} captions.")
            else:
                print(f"Failed to upload {locale} captions: {res.text}")
        except Exception as e:
            print(f"Error uploading caption for locale {locale}: {e}")

    def _publish_to_instagram(self, fb_video_id: str, caption: str):
        """Discovers the linked Instagram Business account and posts the video as an IG Reel."""
        try:
            # 1. Discover Instagram Business Account ID
            discovery_url = f"https://graph.facebook.com/{self.api_version}/{self.page_id}"
            params = {
                "fields": "instagram_business_account",
                "access_token": self.access_token
            }
            disc_res = requests.get(discovery_url, params=params)
            ig_account_id = disc_res.json().get("instagram_business_account", {}).get("id")
            if not ig_account_id:
                print("No linked Instagram Business Account found on Facebook Page. Skipping IG cross-posting.")
                return

            print(f"Found linked Instagram Business Account ID: {ig_account_id}")

            # 2. Get Facebook Video CDN Public source URL
            # We wait up to 60 seconds (with polling) for Facebook to process the video and generate a source URL
            source_url = None
            video_url = f"https://graph.facebook.com/{self.api_version}/{fb_video_id}"
            video_params = {
                "fields": "source",
                "access_token": self.access_token
            }
            
            print("Waiting for Facebook to generate CDN video source URL...")
            for poll in range(12): # Poll every 10 seconds for up to 2 minutes
                video_res = requests.get(video_url, params=video_params)
                source_url = video_res.json().get("source")
                if source_url:
                    break
                time.sleep(10)

            if not source_url:
                print("Could not retrieve Facebook video source URL. Instagram cross-posting aborted.")
                return

            print(f"Successfully retrieved Facebook video source URL: {source_url[:60]}...")

            # 3. Create Instagram Reels Media Container
            container_url = f"https://graph.facebook.com/{self.api_version}/{ig_account_id}/media"
            container_payload = {
                "media_type": "REELS",
                "video_url": source_url,
                "caption": caption,
                "access_token": self.access_token
            }
            c_res = requests.post(container_url, data=container_payload)
            creation_id = c_res.json().get("ig_container_id") or c_res.json().get("id")
            if not creation_id:
                print(f"Failed to create Instagram Reels container: {c_res.text}")
                return

            print(f"Instagram Reels container created! ID: {creation_id}. Processing on Instagram...")

            # 4. Poll IG Container processing state until FINISHED
            status_url = f"https://graph.facebook.com/{self.api_version}/{creation_id}"
            status_params = {
                "fields": "status_code",
                "access_token": self.access_token
            }
            
            processing_success = False
            for poll in range(20): # Poll every 10 seconds for up to 200 seconds
                time.sleep(10)
                status_res = requests.get(status_url, params=status_params)
                status_code = status_res.json().get("status_code")
                print(f"IG Reels Container Status: {status_code}")
                if status_code == "FINISHED":
                    processing_success = True
                    break
                elif status_code in ["ERROR", "EXPIRED"]:
                    print(f"IG Reels Container processing error: {status_res.text}")
                    break

            if not processing_success:
                print("Instagram Reel processing timed out or failed.")
                return

            # 5. Publish IG Reel
            publish_url = f"https://graph.facebook.com/{self.api_version}/{ig_account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            pub_res = requests.post(publish_url, data=publish_payload)
            pub_data = pub_res.json()
            if "id" in pub_data:
                print(f"Instagram Reel published successfully! Media ID: {pub_data['id']}")
            else:
                print(f"Failed to publish Instagram Reel: {pub_res.text}")
        except Exception as e:
            print(f"Error in _publish_to_instagram: {e}")
