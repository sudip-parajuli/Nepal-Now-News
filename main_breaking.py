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
    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.aljazeera.com/rss/world",
    "https://www.reutersagency.com/feed/?best-topics=world-news&post_type=best"
]
POSTED_FILE = "storage/posted_breaking.json"

async def main():
    if not os.path.exists("storage"):
        os.makedirs("storage")
    
    if os.path.exists(POSTED_FILE):
        with open(POSTED_FILE, 'r') as f:
            posted_hashes = json.load(f)
    else:
        posted_hashes = []

    fetcher = RSSFetcher(FEEDS)
    news_items = fetcher.fetch_all()

    classifier = NewsClassifier()
    breaking_news = classifier.filter_breaking(news_items)

    from media.image_fetcher import ImageFetcher
    img_fetcher = ImageFetcher()
    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    vgen = VideoShortsGenerator()
    uploader = YouTubeUploader() if (os.path.exists("client_secrets.json") or os.path.exists("client_secret.json") or os.getenv("YOUTUBE_TOKEN_BASE64")) else None

    for item in breaking_news:
        if item['hash'] not in posted_hashes:
            print(f"Processing breaking news: {item['headline']}")
            
            script = rewriter.rewrite_for_shorts(item['headline'], item['content'])
            
            audio_path = f"storage/temp_audio_{item['hash'][:8]}.mp3"
            _, word_offsets = await TTSEngine.generate_audio(script, audio_path)
            
            # Fetch multiple images based on script segments
            sentences = [s.strip() for s in script.split('.') if len(s.strip()) > 10]
            if not sentences: sentences = [item['headline']]
            
            # Use AI to get better keywords for each segment
            image_queries = []
            for s in sentences[:4]:
                kw = rewriter.generate_image_keywords(s)
                image_queries.append(kw)
                print(f"Segment keywords: {kw}")
                
            image_paths = img_fetcher.fetch_multi_images(image_queries, f"img_{item['hash'][:8]}")
            
            video_path = f"storage/breaking_{item['hash'][:8]}.mp4"
            vgen.create_shorts(script, audio_path, video_path, word_offsets=word_offsets, image_paths=image_paths)
            
            if uploader:
                title = f"BREAKING: {item['headline'][:70]}"
                uploader.upload_video(
                    video_path, 
                    title, 
                    f"Breaking News Update. {script}\n\n#BreakingNews #WorldNews #Shorts", 
                    ["BreakingNews", "WorldNews", "Shorts"]
                )
            
            posted_hashes.append(item['hash'])
            # Clean up
            if os.path.exists(audio_path): os.remove(audio_path)
            for p in image_paths: 
                if os.path.exists(p): os.remove(p)
            break 

    with open(POSTED_FILE, 'w') as f:
        json.dump(posted_hashes[-100:], f)

if __name__ == "__main__":
    asyncio.run(main())
