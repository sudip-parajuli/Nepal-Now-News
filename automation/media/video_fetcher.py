import os
import subprocess
import time
from duckduckgo_search import DDGS

class VideoFetcher:
    def __init__(self, download_dir="automation/storage/temp_videos"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_stock_videos(self, query: str, count: int = 3, topic_context: str = None) -> list:
        """
        Searches for stock videos.
        """
        # Incorporate topic context to ensure relevance (e.g., Space or Ocean)
        if topic_context:
            search_query = f"{topic_context} {query} stock video -person -text -interview -talking -speaker -host"
        else:
            search_query = f"{query} stock video -person -text -interview -talking -speaker -host"
            
        print(f"Searching stock videos for: {search_query}...")
        results = []
        paths = []

        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(search_query, max_results=20)
                for r in search_results:
                    url = r['href']
                    # Broaden the list of supported sites
                    if any(x in url for x in ['pexels.com', 'pixabay.com', 'mixkit.co', 'coverr.co', 'videezy.com', 'videvo.net']):
                        results.append(url)
                    if len(results) >= count * 3: break
        except Exception as e:
            print(f"DDG Search error for videos: {e}")

        # Fallback Strategy: If no results, try broader cinematic terms
        if not results:
            f_topic = topic_context if topic_context else ""
            fallbacks = [
                f"{f_topic} {query} nature background", f"{f_topic} abstract high-tech motion", 
                f"{f_topic} cinematic space", f"{f_topic} microscopic science",
                f"{f_topic} professional 4k background"
            ]
            for f_query in fallbacks:
                print(f"No results for '{query}'. Trying fallback: {f_query}")
                try:
                    with DDGS() as ddgs:
                        search_results = ddgs.text(f_query + " stock video -person", max_results=10)
                        for r in search_results:
                            if any(x in r['href'] for x in ['pexels', 'pixabay', 'mixkit']):
                                results.append(r['href'])
                        if results: break
                except: continue

        for i, url in enumerate(results):
            filename = f"vid_{int(time.time())}_{i}.mp4"
            path = self._download_with_ytdlp(url, filename)
            if path:
                paths.append(path)
            if len(paths) >= count:
                break
        
        return paths

    def _download_with_ytdlp(self, url: str, filename: str) -> str:
        save_path = os.path.join(self.download_dir, filename)
        try:
            cmd = [
                'yt-dlp',
                '-f', 'bestvideo[height<=1080][ext=mp4]/best[ext=mp4]/best',
                '--max-filesize', '35M',
                '--no-playlist',
                '--merge-output-format', 'mp4',
                '-o', save_path,
                url
            ]
            print(f"Downloading video from {url}...")
            result = subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            if os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
                return save_path
        except Exception as e:
            print(f"yt-dlp download failed for {url}: {e}")
        return None
