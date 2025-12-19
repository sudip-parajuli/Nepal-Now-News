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
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.aljazeera.com/rss/world"
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

    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    script = rewriter.summarize_for_daily(normal_news)
    
    audio_path = "storage/daily_summary.mp3"
    await TTSEngine.generate_audio(script, audio_path)
    
    vgen = VideoLongGenerator()
    sections = []
    lines = script.split('.')
    for line in lines:
        if len(line.strip()) > 10:
            sections.append({'text': line.strip(), 'image_path': None})
    
    video_path = "storage/daily_summary.mp4"
    if sections:
        vgen.create_daily_summary(sections, audio_path, video_path)
    
        uploader = YouTubeUploader() if (os.path.exists("client_secrets.json") or os.path.exists("client_secret.json") or os.getenv("YOUTUBE_TOKEN_BASE64")) else None
        if uploader:
            uploader.upload_video(
                video_path,
                f"World News Today | {datetime.now().strftime('%Y-%m-%d')} Global Headlines",
                f"Global news summary for today.\n\nSummary:\n{script}",
                ["WorldNews", "DailyNews", "Summary"],
                category_id="25"
            )

if __name__ == "__main__":
    asyncio.run(main())
