import os
import subprocess
import time
from duckduckgo_search import DDGS

class VideoFetcher:
    def __init__(self, download_dir="automation/storage/temp_videos"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_stock_videos(self, query: str, count: int = 3) -> list:
        """
        Searches for stock videos on Pixabay, Pexels, Mixkit, Coverr, Videezy, or Videvo.
        """
        search_query = f"(site:pexels.com OR site:pixabay.com OR site:mixkit.co OR site:coverr.co OR site:videezy.com OR site:videvo.net) {query} stock video"
        print(f"Searching stock videos for: {search_query}...")
        results = []
        paths = []

        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(search_query, max_results=30)
                for r in search_results:
                    url = r['href']
                    if any(x in url for x in ['pexels.com/video', 'pixabay.com/videos', 'mixkit.co', 'coverr.co', 'videezy.com', 'videvo.net']):
                        results.append(url)
                    if len(results) >= count * 3: break
        except Exception as e:
            print(f"DDG Search error for videos: {e}")

        # Fallback Strategy: If no results, try broader terms
        if not results:
            fallbacks = ["space universe cinema", "nebula galaxy 4k", "deep space background"]
            for f_query in fallbacks:
                print(f"No results for '{query}'. Trying fallback: {f_query}")
                search_query = f"(site:pexels.com OR site:pixabay.com OR site:mixkit.co OR site:videvo.net) {f_query} stock video"
                try:
                    with DDGS() as ddgs:
                        search_results = ddgs.text(search_query, max_results=10)
                        for r in search_results:
                            url = r['href']
                            if any(x in url for x in ['pexels', 'pixabay', 'mixkit', 'videvo']):
                                results.append(url)
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
