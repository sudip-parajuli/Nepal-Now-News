import os
import subprocess
from duckduckgo_search import DDGS

class VideoFetcher:
    def __init__(self, download_dir="automation/storage/temp_videos"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_stock_videos(self, query: str, count: int = 3) -> list:
        """
        Searches for stock videos on Pixabay, Pexels, Mixkit, Coverr, or Videezy.
        """
        search_query = f"(site:pexels.com OR site:pixabay.com OR site:mixkit.co OR site:coverr.co OR site:videezy.com) {query} stock video"
        print(f"Searching stock videos for: {search_query}...")
        results = []
        paths = []

        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(search_query, max_results=20)
                for r in search_results:
                    url = r['href']
                    if any(x in url for x in ['pexels.com/video', 'pixabay.com/videos', 'mixkit.co', 'coverr.co', 'videezy.com']):
                        results.append(url)
                    if len(results) >= count * 4: break
        except Exception as e:
            print(f"DDG Search error for videos: {e}")

        # Retry with simpler query if no results
        if not results and len(query.split()) > 2:
            simpler_query = " ".join(query.split()[:2])
            print(f"No videos found. Retrying with simpler query: {simpler_query}")
            return self.fetch_stock_videos(simpler_query, count)

        for i, url in enumerate(results):
            filename = f"vid_{i}_{int(time.time())}.mp4"
            path = self._download_with_ytdlp(url, filename)
            if path:
                paths.append(path)
            if len(paths) >= count:
                break
        
        return paths

    def _download_with_ytdlp(self, url: str, filename: str) -> str:
        save_path = os.path.join(self.download_dir, filename)
        try:
            # Added more robust format selection for stock sites
            cmd = [
                'yt-dlp',
                '-f', 'bestvideo[height<=1080][ext=mp4]/best[ext=mp4]/best',
                '--max-filesize', '30M',
                '--no-playlist',
                '--merge-output-format', 'mp4',
                '-o', save_path,
                url
            ]
            print(f"Downloading video from {url}...")
            result = subprocess.run(cmd, check=True, capture_output=True)
            if os.path.exists(save_path):
                return save_path
        except Exception as e:
            print(f"yt-dlp download failed for {url}: {e}")
        return None
