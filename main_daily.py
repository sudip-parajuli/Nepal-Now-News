import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from fetchers.rss_fetcher import RSSFetcher
from processors.classifier import NewsClassifier
from processors.rewrite_breaking import ScriptRewriter
from media.tts_english import TTSEngine
from media.video_long import VideoLongGenerator
from uploader.youtube_uploader import YouTubeUploader

load_dotenv()

FEEDS = [
    "https://www.onlinekhabar.com/feed",
    "https://ratopati.com/feed",
    "https://setopati.com/feed",
    "https://www.bbc.com/nepali/index.xml"
]

async def main():
    if not os.path.exists("storage"):
        os.makedirs("storage")

    fetcher = RSSFetcher(FEEDS)
    news_items = fetcher.fetch_all()
    
    classifier = NewsClassifier()
    normal_news = [item for item in news_items if classifier.classify(item) == "NORMAL"][:10]
    
    if not normal_news:
        print("No news to summarize.")
        return

    from media.image_fetcher import ImageFetcher
    img_fetcher = ImageFetcher()
    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    script = rewriter.summarize_for_daily(normal_news)
    
    audio_path = "storage/daily_summary.mp3"
    _, word_offsets = await TTSEngine.generate_audio(script, audio_path)
    
    vgen = VideoLongGenerator()
    sections = []
    lines = script.split('.')
    temp_images = []
    
    print("Fetching images for summary sections...")
    for i, line in enumerate(lines):
        text = line.strip()
        if len(text) > 20:
            # Generate AI keywords for better image context
            keywords = rewriter.generate_image_keywords(text)
            img_name = f"summary_img_{i}.jpg"
            print(f"Section {i} keywords: {keywords}")
            img_path = img_fetcher.fetch_image(keywords, img_name)
            sections.append({'text': text, 'image_path': img_path})
            if img_path: temp_images.append(img_path)
    
    video_path = "storage/daily_summary.mp4"
    if sections:
        vgen.create_daily_summary(sections, audio_path, video_path)
    
        youtube_token = os.getenv("YOUTUBE_TOKEN_BASE64")
        has_secrets = os.path.exists("client_secrets.json") or os.path.exists("client_secret.json")
        
        if youtube_token or has_secrets:
            uploader = YouTubeUploader()
        else:
            print("WARNING: YouTube Uploader not initialized. Missing YOUTUBE_TOKEN_BASE64 secret or client_secrets.json file.")
            uploader = None

        if uploader:
            uploader.upload_video(
                video_path,
                f"आजको प्रमुख समाचार | {datetime.now().strftime('%Y-%m-%d')} प्रमुख खबरहरू",
                f"आजका मुख्य समाचारहरूको सारांश।\n\nSummary:\n{script}\n\n#NepaliNews #DailyNews #Summary",
                ["NepaliNews", "DailyNews", "Summary"],
                category_id="25"
            )

if __name__ == "__main__":
    asyncio.run(main())
