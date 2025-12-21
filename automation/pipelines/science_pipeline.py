import os
import asyncio
from .base_pipeline import BasePipeline
from ..content.science_topic_generator import ScienceTopicGenerator
from ..content.script_writer import ScriptWriter
from ..media.image_fetcher import ImageFetcher
from ..media.video_fetcher import VideoFetcher
from ..media.tts import TTSEngine
from ..media.video_shorts import VideoShortsGenerator
from ..media.nasa_fetcher import NASAFetcher
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
        self.nasa_fetcher = NASAFetcher()
        self.uploader = None # Initialized in run()

    async def run(self, mode="shorts", is_test=False):
        print(f"--- Starting Science Pipeline [{mode}] for {self.config.get('channel_id')} ---")
        
        # 1. Generate Topic
        topic = self.topic_gen.get_next_topic(self.script_writer)
        print(f"Topic: {topic}")
        
        if mode == "shorts":
            await self._run_shorts(topic, is_test)
        elif mode == "daily":
            await self._run_daily(topic, is_test)
        
        print(f"--- Science Pipeline [{mode}] Completed ---")

    async def _run_shorts(self, topic: str, is_test: bool):
        # 2. Generate Script
        script = self.script_writer.generate_science_facts(topic)
        print(f"Short Script generated.")
        
        # 3. Fetch Media
        media_paths = await self._fetch_media(topic, script)
            
        # 4. Generate Audio
        male_voice = self.config.get('tts_voice', {}).get('male', "en-US-GuyNeural")
        audio_path = "automation/storage/science_shorts_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path, voice=male_voice)
        
        # 5. Create Video
        video_path = "automation/storage/science_shorts_final.mp4"
        self.vgen.create_shorts(
            script, 
            audio_path, 
            video_path, 
            word_offsets=word_offsets, 
            media_paths=media_paths,
            branding=self.config.get('branding')
        )
        
        # 6. Upload
        if True: # Always call _upload, it handles is_test internally
            await self._upload(video_path, f"{topic} #Shorts", script, topic, is_test=is_test)

    async def _run_daily(self, topic: str, is_test: bool):
        # 2. Generate Expanded Script
        script = self.script_writer.expand_science_script(topic)
        print(f"Expanded Script generated (~{len(script.split())} words).")
        
        # 3. Fetch Media (More for long form)
        media_paths = await self._fetch_media(topic, script, count_per_kw=2)
            
        # 4. Generate Audio
        male_voice = self.config.get('tts_voice', {}).get('male', "en-US-GuyNeural")
        audio_path = "automation/storage/science_long_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path, voice=male_voice)
        
        # 5. Create Long Video (Detailed)
        # For now we use VideoLongGenerator but with segments for the same topic
        segments = [{"type": "science", "text": script, "topic": topic}]
        video_path = "automation/storage/science_long_final.mp4"
        
        # Use VideoLongGenerator
        from ..media.video_long import VideoLongGenerator
        vgen_long = VideoLongGenerator()
        vgen_long.create_daily_summary(segments, audio_path, video_path, word_offsets, media_paths=media_paths)
        
        # 6. Upload
        if True: # Always call _upload, it handles is_test internally
            await self._upload(video_path, f"The Science of {topic}: Detailed Explanation", script, topic, is_test=is_test, is_shorts=False)

    async def _fetch_media(self, topic, script, count_per_kw=1):
        print("Fetching multi-segment media...")
        keywords_list = self.script_writer.generate_image_keywords(script, extra_context=topic)
        media_paths = []
        
        for i, kw in enumerate(keywords_list):
            # Priority 1: NASA
            nasa_clips = self.nasa_fetcher.fetch_nasa_videos(kw, count=count_per_kw)
            if nasa_clips:
                media_paths.extend(nasa_clips)
            else:
                # Priority 2: Generic Stock
                clips = self.video_fetcher.fetch_stock_videos(kw, count=count_per_kw)
                media_paths.extend(clips)
        
        if len(media_paths) < 3:
            img_kw = self.script_writer.generate_image_keywords(script, extra_context=f"{topic} cinematic")
            img_paths = self.image_fetcher.fetch_multi_images(img_kw, "science_temp")
            media_paths.extend(img_paths)
        return media_paths

    async def _upload(self, video_path, title, script, topic, is_test=False, is_shorts=True):
        print("Initializing YouTube service...")
        youtube_service = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
        self.uploader = YouTubeUploader(youtube_service)
        
        hashtags = self.config.get('hashtags', "#science #facts #universe")
        description = f"{script}\n\n#Science #Education {hashtags}"
        tags = ["science", "facts", "universe", "space", "educational"]
        if is_shorts: tags.append("shorts")
        
        if not is_test:
            print(f"Uploading: {title}")
            self.uploader.upload_video(video_path, title, description, tags)
        else:
            print(f"TEST MODE: Skipping upload for {title}")
        
        print(f"--- Science Pipeline Completed ---")
