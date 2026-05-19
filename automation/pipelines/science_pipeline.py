import os
import asyncio
import random
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
from ..media.srt_generator import generate_srt

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
        t_v = config.get('tts_voice', {})
        self.tts = TTSEngine(
            voice_map=t_v, 
            rate=t_v.get('rate', "-25%"),
            pitch=t_v.get('pitch', "-12Hz"),
            allow_elevenlabs=False
        )
        self.vgen = VideoShortsGenerator()
        # Default science music volume to 0.04 as requested
        self.music_volume = config.get('branding', {}).get('music_volume', 0.04)
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
        
        # Cleanup temporary files
        self.cleanup_storage()
        print(f"--- Science Pipeline [{mode}] Completed ---")

    async def _run_shorts(self, topic: str, is_test: bool):
        # 2. Generate Script
        # Categories: General, Did You Know, What If
        categories = ["General", "Did You Know?", "What If?"]
        category = random.choice(categories)
        print(f"Selected Category: {category}")
        
        prompt_topic = topic
        if category == "Did You Know?":
            prompt_topic = f"Did you know {topic}?"
        elif category == "What If?":
            prompt_topic = f"What if {topic}?"
            
        script = self.script_writer.generate_science_facts(prompt_topic)
        print(f"Short Script generated ({category}).")
        
        # 3. Fetch Media
        media_paths = await self._fetch_media(prompt_topic, script)
            
        # 4. Generate Audio
        male_voice = self.config.get('tts_voice', {}).get('male', "en-US-GuyNeural")
        audio_path = "automation/storage/science_shorts_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path, voice=male_voice)
        
        # 5. Create Video
        video_path = "automation/storage/science_shorts_final.mp4"
        try:
            print(f"DEBUG: calling val.create_shorts with {len(media_paths)} media items.")
            self.vgen.create_shorts(
                script, 
                audio_path, 
                video_path, 
                word_offsets=word_offsets, 
                media_paths=media_paths,
                branding=self.config.get('branding')
            )
            if os.path.exists(video_path):
                print(f"DEBUG: Science Shorts created successfully at {video_path}")
            else:
                print(f"CRITICAL: Science Shorts creation executed but file missing: {video_path}")
        except Exception as e:
            print(f"CRITICAL ERROR in create_shorts: {e}")
            import traceback
            traceback.print_exc()
            raise e
        
        # 6. Upload
        if True: # Always call _upload, it handles is_test internally
            await self._upload(video_path, f"{topic} #Shorts", script, topic, is_test=is_test)

    async def _run_daily(self, topic: str, is_test: bool):
        # 2. Generate Expanded Script (plain text for TTS — unchanged)
        script = self.script_writer.expand_science_script(topic)
        print(f"Expanded Script generated (~{len(script.split())} words).")

        # 3. Generate Visual Scenes (structured JSON for visual routing)
        print("Generating visual scene classification...")
        scenes_data = self.script_writer.generate_visual_scenes(topic, script)

        # 4. Fetch All Assets via Orchestrator
        asset_manifest = None
        if scenes_data:
            from ..media.asset_orchestrator import AssetOrchestrator
            orchestrator = AssetOrchestrator(hf_token=os.getenv("HF_TOKEN", ""))
            asset_manifest = orchestrator.fetch_all(scenes_data, topic)
            print(f"Asset manifest ready: job_id={asset_manifest.get('job_id')}, "
                  f"{len(asset_manifest.get('scenes', []))} scenes.")
        else:
            print("WARNING: No visual scenes generated. Falling back to image-only pipeline.")

        # 5. Fetch fallback media_paths (used if asset_manifest failed entirely)
        media_paths = None
        if not asset_manifest:
            media_paths = await self._fetch_media(topic, script, count_per_kw=2, is_long_form=True)

        # 6. Generate Audio
        male_voice = self.config.get('tts_voice', {}).get('male', "en-US-GuyNeural")
        audio_path = "automation/storage/science_long_temp.mp3"
        _, word_offsets = await self.tts.generate_audio(script, audio_path, voice=male_voice)

        # 7. Create Long Video
        segments = [{"type": "science", "text": script, "topic": topic}]
        video_path = "automation/storage/science_long_final.mp4"

        from ..media.video_long import VideoLongGenerator
        vgen_long = VideoLongGenerator()
        vgen_long.create_daily_summary(
            segments,
            audio_path,
            video_path,
            word_offsets,
            media_paths=media_paths,
            asset_manifest=asset_manifest,
        )

        # 8. Cleanup temp job assets after successful render
        if asset_manifest and os.path.exists(video_path):
            from ..media.asset_orchestrator import AssetOrchestrator
            AssetOrchestrator().cleanup(asset_manifest)

        # 9. Generate SRT captions
        srt_path = "automation/storage/science_long.srt"
        generate_srt(word_offsets, srt_path)

        # 10. Generate Thumbnail
        print("Generating automated thumbnail...")
        from ..media.thumbnail_generator import ThumbnailGenerator
        thumb_gen = ThumbnailGenerator()
        thumb_info = scenes_data if scenes_data and 'thumbnail_data' in scenes_data else self.script_writer.generate_thumbnail_info(topic, script)
        thumb_path = thumb_gen.generate_thumbnail(thumb_info)

        # 11. Upload
        if True:
            video_id = await self._upload(
                video_path,
                f"The Science of {topic}: Detailed Explanation",
                script, topic,
                is_test=is_test, is_shorts=False, srt_path=srt_path
            )

            # 12. Upload Thumbnail if video succeeded
            if video_id and thumb_path and os.path.exists(thumb_path) and not is_test:
                print(f"Uploading thumbnail for video {video_id}...")
                self.uploader.upload_thumbnail(video_id, thumb_path)



    async def _fetch_media(self, topic, script, count_per_kw=1, is_long_form=False):
        print(f"Fetching multi-segment media (long_form={is_long_form})...")
        keywords_list = self.script_writer.generate_image_keywords(script, extra_context=topic, is_long_form=is_long_form)
        media_paths = []
        
        # Fetching images for all keywords
        # Generating a mix of "cinematic", "macro", "detailed" searches
        combined_keywords = []
        for kw in keywords_list:
            # Variety of search modifiers
            combined_keywords.append(f"{kw} cinematic 4k")
            if is_long_form:
                combined_keywords.append(f"{kw} close up macro")
            
        print(f"Fetching {len(combined_keywords)} potential images for Science content...")
        img_paths = self.image_fetcher.fetch_multi_images(combined_keywords, "science_temp", topic_context=topic)
        media_paths.extend(img_paths)
        
        return media_paths
        
        
        return media_paths

    async def _upload(self, video_path, title, script, topic, is_test=False, is_shorts=True, srt_path=None):
        print("Initializing YouTube service...")
        youtube_service = YouTubeAuth.get_service(os.getenv("YOUTUBE_TOKEN_BASE64"))
        self.uploader = YouTubeUploader(youtube_service)
        
        hashtags = self.config.get('hashtags', "#science #facts #universe")
        description = f"{script}\n\n#Science #Education {hashtags}"
        tags = ["science", "facts", "universe", "space", "educational"]
        if is_shorts: tags.append("shorts")
        
        video_id = None
        if not is_test:
            print(f"Uploading: {title}")
            video_id = self.uploader.upload_video(video_path, title, description, tags)
            
            # If we have an SRT file, upload it as captions
            if video_id and srt_path and os.path.exists(srt_path):
                print(f"Uploading captions from {srt_path}...")
                try:
                    self.uploader.upload_caption(video_id, srt_path)
                except Exception as e:
                    print(f"WARNING: Caption upload failed: {e}")
                    print("This might be due to insufficient authentication scopes (youtube.force-ssl required).")
        else:
            print(f"TEST MODE: Skipping upload for {title}")
            video_id = "test_video_id"
        
        print(f"--- Science Pipeline Completed ---")
        return video_id
