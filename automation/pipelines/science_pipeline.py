import os
import asyncio
from .base_pipeline import BasePipeline
from ..content.science_topic_generator import ScienceTopicGenerator
from ..content.script_writer import ScriptWriter
from ..media.image_fetcher import ImageFetcher
from ..media.tts import TTSEngine
from ..media.video_shorts import VideoShortsGenerator
from ..youtube.uploader import YouTubeUploader
from ..youtube.auth import YouTubeAuth

class SciencePipeline(BasePipeline):
    def __init__(self, config):
        super().__init__(config)
        self.script_writer = ScriptWriter(os.getenv("GEMINI_API_KEY"))
        self.topic_gen = ScienceTopicGenerator(
            config['storage']['topic_history'],
            config['topics']
        )
        self.image_fetcher = ImageFetcher()
        self.tts = TTSEngine(voice_map=config['tts_voice'], rate="+15%") # Slower for science
        self.vgen = VideoShortsGenerator()
        self.uploader = None # Initialized in run()

    async def run(self, is_test=False):
        print(f"--- Starting Science Pipeline for {self.config.get('channel_id')} ---")
        
        # 1. Generate Topic
        topic = self.topic_gen.get_next_topic(self.script_writer)
        print(f"Topic: {topic}")
        
        # 2. Generate Script
        script = self.script_writer.generate_science_facts(topic)
        print(f"Script generated ({len(script)} chars).")
        
        # 3. Fetch Images
        keywords = self.script_writer.generate_image_keywords(topic, extra_context="Scientific Documentary")
        image_queries = [keywords] * 5 # Get 5 images for rotation
        image_paths = self.image_fetcher.fetch_multi_images(image_queries, "science_temp")
        
        # 4. Generate Audio
        audio_path = "automation/storage/science_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path)
        
        # 5. Create Video
        video_path = "automation/storage/science_final.mp4"
        self.vgen.create_shorts(
            script, 
            audio_path, 
            video_path, 
            word_offsets=word_offsets, 
            image_paths=image_paths
        )
        
        # 6. Upload
        if not is_test:
            print("Initializing YouTube service...")
            youtube_service = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
            self.uploader = YouTubeUploader(youtube_service)
            
            title = f"{topic} #Science #Facts #Universe #Shorts"
            description = f"Did you know about {topic}? Learn more about the amazing secrets of our universe. #science #nepali #facts"
            tags = ["science", "facts", "nepali", "universe", "space", "shorts"]
            
            print(f"Uploading: {title}")
            self.uploader.upload_video(video_path, title, description, tags)
        else:
            print("TEST MODE: Skipping upload.")
        
        print(f"--- Science Pipeline Completed ---")
