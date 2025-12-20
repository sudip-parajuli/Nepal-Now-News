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
        
        # 3. Fetch Background Media (Multi-Segment for variety)
        print("Fetching multi-segment media...")
        keywords_list = self.script_writer.generate_image_keywords(script, extra_context=topic)
        media_paths = []
        
        for i, kw in enumerate(keywords_list):
            print(f"Searching media for scene {i+1}: {kw}")
            clips = self.video_fetcher.fetch_stock_videos(kw, count=1)
            media_paths.extend(clips)
        
        if len(media_paths) < 2:
            print("Not enough videos found, fetching high-quality images...")
            img_kw = self.script_writer.generate_image_keywords(script, extra_context=f"{topic} cinematic")
            img_paths = self.image_fetcher.fetch_multi_images(img_kw, "science_temp")
            media_paths.extend(img_paths)
            
        # 4. Generate Audio
        print("Generating Audio...")
        # Use a calm male voice
        self.tts.voice_map['male'] = self.config.get('tts_voice', {}).get('male', "en-US-GuyNeural")
        
        audio_path = "automation/storage/science_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path)
        
        # 5. Create Video (Now supports mixed media and branding)
        video_path = "automation/storage/science_final.mp4"
        self.vgen.create_shorts(
            script, 
            audio_path, 
            video_path, 
            word_offsets=word_offsets, 
            media_paths=media_paths,
            branding=self.config.get('branding')
        )
        
        # 6. Upload
        if not is_test:
            print("Initializing YouTube service...")
            youtube_service = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
            self.uploader = YouTubeUploader(youtube_service)
            
            hashtags = self.config.get('hashtags', "#science #facts #universe #shorts")
            title = f"{topic} #Shorts" # Keep title clean, hashtags in description
            description = f"Did you know about {topic}? Dive into the amazing secrets of our universe.\n\n{hashtags}"
            tags = ["science", "facts", "universe", "space", "shorts", "educational"]
            
            print(f"Uploading: {title}")
            self.uploader.upload_video(video_path, title, description, tags)
        else:
            print("TEST MODE: Skipping upload.")
        
        print(f"--- Science Pipeline Completed ---")
