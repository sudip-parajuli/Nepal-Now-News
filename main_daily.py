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
from media.image_fetcher import ImageFetcher
from uploader.youtube_uploader import YouTubeUploader

load_dotenv()

FEEDS = [
    "https://www.onlinekhabar.com/feed",
    "https://ratopati.com/feed",
    "https://setopati.com/feed",
    "https://www.bbc.com/nepali/index.xml",
    "https://www.ronbpost.com/category/news/feed/"
]

async def main():
    if not os.path.exists("storage"):
        os.makedirs("storage")

    fetcher = RSSFetcher(FEEDS)
    news_items = fetcher.fetch_all()
    
    classifier = NewsClassifier()
    # Filter for normal news items
    normal_news = [item for item in news_items if classifier.classify(item) == "NORMAL"][:10]
    
    if not normal_news:
        print("No news to summarize.")
        return

    img_fetcher = ImageFetcher()
    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    
    print("Generating structured daily summary script...")
    segments = rewriter.summarize_for_daily(normal_news)
    
    if not isinstance(segments, list):
        print("Error: Generated script is not in segment format.")
        return

    # 1. Fetch Images for each segment (specifically news headlines)
    print("Fetching relevant images for segments...")
    for i, seg in enumerate(segments):
        if seg.get("type") == "news" and seg.get("headline"):
            # Use headline for precise image context
            keywords = rewriter.generate_image_keywords(seg["headline"])
            img_name = f"summary_headline_{i}.jpg"
            img_path = img_fetcher.fetch_image(keywords, img_name)
            seg["image_path"] = img_path
        elif seg.get("type") == "intro":
            # Generic news anchor/broadcast image
            seg["image_path"] = img_fetcher.fetch_image("Nepali news studio background", "intro_bg.jpg")
        elif seg.get("type") == "outro":
            seg["image_path"] = img_fetcher.fetch_image("Thank you for watching news", "outro_bg.jpg")

    # 2. Generate Multi-vocal Audio
    audio_path = "storage/daily_summary.mp3"
    print("Generating multi-vocal narration...")
    _, word_offsets, durations = await TTSEngine.generate_multivocal_audio(segments, audio_path)
    
    # 3. Create Video
    video_path = "storage/daily_summary_final.mp4"
    vgen = VideoLongGenerator()
    print("Creating final video summary...")
    vgen.create_daily_summary(segments, audio_path, video_path, word_offsets, durations=durations)
    
    # 4. Upload to YouTube
    youtube_token = os.getenv("YOUTUBE_TOKEN_BASE64")
    has_secrets = os.path.exists("client_secrets.json") or os.path.exists("client_secret.json")
    
    if youtube_token or has_secrets:
        uploader = YouTubeUploader()
        uploader.upload_video(
            video_path,
            f"आजको प्रमुख समाचार | {datetime.now().strftime('%Y-%m-%d')} प्रमुख खबरहरू",
            f"आजका मुख्य समाचारहरूको सारांश।\n\n#NepaliNews #DailyNews #Summary #NepalNow",
            ["NepaliNews", "DailyNews", "Summary"],
            category_id="25"
        )
    else:
        print("YouTube uploader not configured. Skipping upload.")

if __name__ == "__main__":
    asyncio.run(main())
