import os
import asyncio
from .base_pipeline import BasePipeline
from ..content.science_topic_generator import ScienceTopicGenerator
from ..content.script_writer import ScriptWriter
from ..media.image_fetcher import ImageFetcher
from ..media.video_fetcher import VideoFetcher
from ..media.tts import TTSEngine
from ..media.video_shorts import VideoShortsGenerator
from ..youtube.uploader import YouTubeUploader
from ..youtube.auth import YouTubeAuth

class SciencePipeline(BasePipeline):
    def __init__(self, config):
        super().__init__(config)
        self.script_writer = ScriptWriter(os.getenv("GEMINI_API_KEY"))
        self.topic_gen = ScienceTopicGenerator(
            config['storage']['posted_science'],
            config['topics']
        )
        self.image_fetcher = ImageFetcher()
        self.video_fetcher = VideoFetcher()
        self.tts = TTSEngine(voice_map=config['tts_voice'], rate="+15%") # Slower for science
        self.vgen = VideoShortsGenerator()
        self.uploader = None # Initialized in run()

    async def run(self, is_test=False):
        print(f"--- Starting Science Pipeline for {self.config.get('channel_id')} ---")
        
        # 1. Generate Topic
        topic = self.topic_gen.get_next_topic(self.script_writer)
        print(f"Topic: {topic}")
        
        # 2. Generate Script (Now includes engagement question)
        script = self.script_writer.generate_science_facts(topic)
        print(f"Script generated ({len(script)} chars).")
        
        # 3. Fetch Background Media (Prioritize Videos)
        keywords = self.script_writer.generate_image_keywords(topic, extra_context="Scientific Documentary")
        print(f"Keywords: {keywords}")
        
        # Try fetching videos first
        media_paths = self.video_fetcher.fetch_stock_videos(keywords, count=2)
        
        # Fallback to images if not enough videos
        if len(media_paths) < 2:
            print("Not enough videos found, fetching some high-quality images...")
            img_paths = self.image_fetcher.fetch_multi_images([keywords] * 3, "science_temp")
            media_paths.extend(img_paths)
        
        # 4. Generate Audio
        audio_path = "automation/storage/science_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path)
        
        # 5. Create Video (Now supports mixed media)
        video_path = "automation/storage/science_final.mp4"
        self.vgen.create_shorts(
            script, 
            audio_path, 
            video_path, 
            word_offsets=word_offsets, 
            media_paths=media_paths
        )
        
        # 6. Upload
        if not is_test:
            print("Initializing YouTube service...")
            youtube_service = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
            self.uploader = YouTubeUploader(youtube_service)
            
            title = f"{topic} #Science #Facts #Universe #Shorts"
            description = f"Did you know about {topic}? Dive into the amazing secrets of our universe. #science #facts #space #shorts"
            tags = ["science", "facts", "universe", "space", "shorts", "educational"]
            
            print(f"Uploading: {title}")
            self.uploader.upload_video(video_path, title, description, tags)
        else:
            print("TEST MODE: Skipping upload.")
        
        print(f"--- Science Pipeline Completed ---")
