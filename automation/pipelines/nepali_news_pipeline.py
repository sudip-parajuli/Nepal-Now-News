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

class NepaliNewsPipeline(BasePipeline):
    def __init__(self, config):
        super().__init__(config)
        self.fetcher = RSSFetcher(config['feeds'])
        self.classifier = NewsClassifier()
        self.script_writer = ScriptWriter(os.getenv("GEMINI_API_KEY"))
        self.image_fetcher = ImageFetcher()
        self.tts = TTSEngine(voice_map=config['tts_voice'], rate="+15%")
        self.vgen_shorts = VideoShortsGenerator()
        self.vgen_long = VideoLongGenerator()
        self.posted_file = config['storage']['posted_news']

    async def run(self, mode="breaking", is_test=False):
        """
        Runs the news pipeline.
        mode: "breaking" (Shorts) or "daily" (Long/Summary)
        """
        print(f"--- Starting News Pipeline [{mode}] ---")
        news_items = self.fetcher.fetch_all()
        
        if mode == "breaking":
            await self._run_breaking(news_items, is_test)
        elif mode == "daily":
            await self._run_daily(news_items, is_test)
        
        print(f"--- News Pipeline [{mode}] Completed ---")

    async def _run_breaking(self, news_items: List[Dict], is_test: bool):
        posted_hashes = self._load_posted_hashes()
        breaking_news = self.classifier.filter_breaking(news_items)
        
        count = 0
        for item in breaking_news:
            if item['hash'] not in posted_hashes:
                print(f"New Breaking: {item['headline']}")
                script = self.script_writer.rewrite_for_shorts(item['headline'], item['content'])
                
                audio_path = f"automation/storage/news_breaking_{item['hash'][:8]}.mp3"
                _, word_offsets = await self.tts.generate_audio(script, audio_path)
                
                kw = self.script_writer.generate_image_keywords(item['headline'])
                image_paths = self.image_fetcher.fetch_multi_images([kw]*5, f"news_{item['hash'][:8]}")
                
                video_path = f"automation/storage/news_breaking_{item['hash'][:8]}.mp4"
                self.vgen_shorts.create_shorts(script, audio_path, video_path, word_offsets=word_offsets, media_paths=image_paths)
                
                if not is_test:
                    yt = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
                    uploader = YouTubeUploader(yt)
                    title = f"BREAKING: {item['headline'][:70]}"
                    uploader.upload_video(video_path, title, f"{script}\n#News #Nepal", ["News", "Nepal"])
                
                posted_hashes.append(item['hash'])
                self._save_posted_hashes(posted_hashes)
                count += 1
                if count >= 2: break
        
    async def _run_daily(self, news_items: List[Dict], is_test: bool):
        # Limit to last 10 items for summary
        summary_segments = self.script_writer.summarize_for_daily(news_items[:10])
        
        # Fetch images for segments
        for seg in summary_segments:
            if seg.get("type") == "news":
                kw = self.script_writer.generate_image_keywords(seg['headline'])
                path = self.image_fetcher.fetch_image(kw, f"daily_{seg['headline'][:10]}.jpg")
                seg['image_path'] = path
        
        audio_path = "automation/storage/daily_temp.mp3"
        _, word_offsets, durations = await self.tts.generate_multivocal_audio(summary_segments, audio_path)
        
        video_path = "automation/storage/daily_final.mp4"
        self.vgen_long.create_daily_summary(summary_segments, audio_path, video_path, word_offsets, durations)
        
        if not is_test:
            yt = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
            uploader = YouTubeUploader(yt)
            title = f"Daily News Summary - {os.environ.get('CURRENT_DATE', '')}"
            uploader.upload_video(video_path, title, "Today's top updates.", ["News", "Daily"])

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
