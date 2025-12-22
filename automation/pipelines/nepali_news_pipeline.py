import os
import json
import asyncio
from typing import List, Dict
from .base_pipeline import BasePipeline
from ..content.news_fetcher import RSSFetcher
from ..content.classifier import NewsClassifier
from ..content.script_writer import ScriptWriter
from ..media.image_fetcher import ImageFetcher
from ..media.tts import TTSEngine
from ..media.video_shorts import VideoShortsGenerator
from ..media.video_long import VideoLongGenerator
from ..youtube.uploader import YouTubeUploader
from ..youtube.auth import YouTubeAuth

# Storytelling Imports
from ..longform_storytelling.topic_selector import TopicSelector
from ..longform_storytelling.script_writer import ScriptWriter as StoryScriptWriter
from ..longform_storytelling.tts_engine import StoryTTSEngine
from ..longform_storytelling.video_generator import StoryVideoGenerator

class NepaliNewsPipeline(BasePipeline):
    def __init__(self, config):
        super().__init__(config)
        self.fetcher = RSSFetcher(config['feeds'])
        self.classifier = NewsClassifier()
        self.script_writer = ScriptWriter(os.getenv("GEMINI_API_KEY"))
        self.image_fetcher = ImageFetcher()
        self.tts = TTSEngine(voice_map=config['tts_voice'], rate="+15%")
        self.vgen_shorts = VideoShortsGenerator()
        self.vgen_long = VideoLongGenerator() # Keep for other uses if needed
        self.posted_file = config['storage']['posted_news']
        
        # Storytelling Components
        self.topic_selector = TopicSelector()
        self.story_writer = StoryScriptWriter(os.getenv("GEMINI_API_KEY"))
        self.story_tts = StoryTTSEngine()
        self.story_vgen = StoryVideoGenerator()

    async def run(self, mode="breaking", is_test=False):
        """
        Runs the news pipeline.
        mode: "breaking" (Shorts) or "daily" (Long/Summary)
        """
        print(f"--- Starting News Pipeline [{mode}] ---")
        if mode == "breaking":
            news_items = self.fetcher.fetch_all()
            await self._run_breaking(news_items, is_test)
        elif mode == "daily" or mode == "storytelling":
            await self._run_storytelling(is_test)
        
        print(f"--- News Pipeline [{mode}] Completed ---")

    async def _run_breaking(self, news_items: List[Dict], is_test: bool):
        posted_hashes = self._load_posted_hashes()
        breaking_news = self.classifier.filter_breaking(news_items)
        
        # De-duplicate within this run using headline_hash
        unique_breaking = []
        seen_headlines_this_run = set()
        for item in breaking_news:
            h_hash = item.get('headline_hash', item['hash'])
            if h_hash not in seen_headlines_this_run:
                unique_breaking.append(item)
                seen_headlines_this_run.add(h_hash)

        count = 0
        for item in unique_breaking:
            # Check both content hash and headline hash for maximum safety
            h_hash = item.get('headline_hash', item['hash'])
            if item['hash'] not in posted_hashes and h_hash not in posted_hashes:
                print(f"New Breaking: {item['headline']}")
                script = self.script_writer.rewrite_for_shorts(item['headline'], item['content'])
                
                audio_path = f"automation/storage/news_breaking_{item['hash'][:8]}.mp3"
                _, word_offsets = await self.tts.generate_audio(script, audio_path)
                
                if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                    print(f"Skipping breaking news due to TTS failure: {item['headline']}")
                    continue

                video_path = f"automation/storage/news_breaking_{item['hash'][:8]}.mp4"
                self.vgen_shorts.create_shorts(
                    script, 
                    audio_path, 
                    video_path, 
                    word_offsets=word_offsets, 
                    media_paths=[], 
                    template_mode=True,
                    branding=self.config.get('branding')
                )
                
                if not is_test:
                    yt = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
                    uploader = YouTubeUploader(yt)
                    title = f"BREAKING: {item['headline'][:70]}"
                    uploader.upload_video(video_path, title, f"{script}\n#News #Nepal", ["News", "Nepal"])
                
                # Save both hashes to prevent future duplicates
                posted_hashes.append(item['hash'])
                if 'headline_hash' in item:
                    posted_hashes.append(item['headline_hash'])
                
                self._save_posted_hashes(posted_hashes)
                count += 1
                if count >= 2: break
        
    async def _run_storytelling(self, is_test: bool):
        print("Running Storytelling Program: Baje & Arav")
        
        # 1. Select Topic
        topic = self.topic_selector.select_topic()
        print(f"Current Topic ID: {topic['id']}")
        
        # 2. Generate Script
        script = self.story_writer.generate_story_script(topic['title'])
        if not script:
            print("Failed to generate story script.")
            return

        # 3. Generate Dual-Voice Audio
        audio_path = "automation/storage/story_temp.mp3"
        audio_path, _, enriched_script = await self.story_tts.generate_story_audio(script, audio_path)
        
        # 4. Generate Video
        video_path = "automation/storage/story_final.mp4"
        self.story_vgen.create_story_video(enriched_script, audio_path, video_path)
        
        # 5. Upload
        if not is_test:
            yt = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
            uploader = YouTubeUploader(yt)
            title = f"बाजे र Gen-Z: {topic['title']}"
            description = f"हल्का गफ, गहिरो कुरा। \n\nआजको विषय: {topic['title']}\n#Nepal #GenZ #Baje #Storytelling"
            uploader.upload_video(video_path, title, description, ["Nepal", "GenZ", "Stories", "Baje"])

    def _load_posted_hashes(self):
        if os.path.exists(self.posted_file):
            try:
                with open(self.posted_file, 'r') as f: return json.load(f)
            except: return []
        return []

    def _save_posted_hashes(self, hashes):
        os.makedirs(os.path.dirname(self.posted_file), exist_ok=True)
        with open(self.posted_file, 'w') as f:
            json.dump(hashes[-500:], f)
