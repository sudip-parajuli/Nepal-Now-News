import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

from fetchers.rss_fetcher import RSSFetcher
from processors.classifier import NewsClassifier
from processors.rewrite_breaking import ScriptRewriter
from media.tts_english import TTSEngine
from media.video_shorts import VideoShortsGenerator
from uploader.youtube_uploader import YouTubeUploader

load_dotenv()

FEEDS = [
    "https://www.onlinekhabar.com/feed",
    "https://ratopati.com/feed",
    "https://setopati.com/feed",
    "https://www.setopati.com/politics/feed",
    "https://www.bbc.com/nepali/index.xml",
    "https://www.ronbpost.com/category/news/feed/"
]
POSTED_FILE = "storage/posted_breaking_nepali.json"

async def main():
    # Ensure storage exists at the start
    base_dir = os.getcwd()
    storage_dir = os.path.join(base_dir, "storage")
    if not os.path.exists(storage_dir):
        os.makedirs(storage_dir)
    
    posted_path = os.path.join(base_dir, POSTED_FILE)
    
    # Load posted hashes with fallback to root if storage is empty but root has it
    if os.path.exists(posted_path):
        with open(posted_path, 'r') as f:
            posted_hashes = json.load(f)
    elif os.path.exists("posted_breaking.json"):
        with open("posted_breaking.json", 'r') as f:
            posted_hashes = json.load(f)
    else:
        posted_hashes = []

    print(f"Loaded {len(posted_hashes)} previously posted news hashes.")

    fetcher = RSSFetcher(FEEDS)
    news_items = fetcher.fetch_all()
    print(f"Total news items fetched: {len(news_items)}")

    classifier = NewsClassifier()
    breaking_news = classifier.filter_breaking(news_items)
    print(f"Total breaking news items identified: {len(breaking_news)}")

    from media.image_fetcher import ImageFetcher
    img_fetcher = ImageFetcher()
    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    vgen = VideoShortsGenerator()
    youtube_token = os.getenv("YOUTUBE_TOKEN_BASE64")
    has_secrets = os.path.exists("client_secrets.json") or os.path.exists("client_secret.json")
    
    if youtube_token or has_secrets:
        uploader = YouTubeUploader()
    else:
        print("WARNING: YouTube Uploader not initialized. Missing YOUTUBE_TOKEN_BASE64 secret or client_secrets.json file.")
        uploader = None

    processed_count = 0
    for item in breaking_news:
        if item['hash'] not in posted_hashes:
            print(f"NEW Breaking News detected: {item['headline']}")
            
            script = rewriter.rewrite_for_shorts(item['headline'], item['content'])
            
            audio_path = os.path.join(storage_dir, f"temp_audio_{item['hash'][:8]}.mp3")
            _, word_offsets = await TTSEngine.generate_audio(script, audio_path)
            
            # Fetch multiple images
            sentences = [s.strip() for s in script.split('.') if len(s.strip()) > 10]
            if not sentences: sentences = [item['headline']]
            
            image_queries = []
            for s in sentences[:10]:
                kw = rewriter.generate_image_keywords(s)
                image_queries.append(kw)
                
            image_paths = img_fetcher.fetch_multi_images(image_queries, f"img_{item['hash'][:8]}")
            
            video_path = os.path.join(storage_dir, f"breaking_{item['hash'][:8]}.mp4")
            vgen.create_shorts(script, audio_path, video_path, word_offsets=word_offsets, image_paths=image_paths)
            
            if uploader:
                title = f"BREAKING: {item['headline'][:70]}"
                print(f"Uploading to YouTube: {title}")
                uploader.upload_video(
                    video_path, 
                    title, 
                    f"आजको ताजा समाचार (Nepali News Update). {script}\n\n#NepaliNews #NewsNepal #BreakingNewsNepal #Shorts", 
                    ["NepaliNews", "NewsNepal", "BreakingNewsNepal", "Shorts"]
                )
            
            posted_hashes.append(item['hash'])
            # Save immediately to prevent issues if process crashes
            with open(posted_path, 'w') as f:
                json.dump(posted_hashes[-200:], f)
                
            # Clean up
            if os.path.exists(audio_path): os.remove(audio_path)
            for p in image_paths: 
                if os.path.exists(p): os.remove(p)
            
            processed_count += 1
            if processed_count >= 2: # Limit to 2 per run to avoid overwhelming
                break 
        else:
            print(f"Skipping already posted news: {item['headline']}")

if __name__ == "__main__":
    asyncio.run(main())
