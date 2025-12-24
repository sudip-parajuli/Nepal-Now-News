import os
import requests
import json
import time

class NASAFetcher:
    def __init__(self, download_dir="automation/storage/temp_videos"):
        self.download_dir = download_dir
        self.base_url = "https://images-api.nasa.gov"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_nasa_videos(self, query: str, count: int = 1) -> list:
        """
        Searches NASA Image and Video Library for mp4 videos.
        Returns a list of local file paths.
        """
        print(f"Searching NASA Library for: {query}...")
        simplified_query = " ".join(query.split()[-2:]) if len(query.split()) > 2 else query
        
        search_url = f"{self.base_url}/search"
        params = {
            "q": simplified_query,
            "media_type": "video"
        }
        
        paths = []
        try:
            response = requests.get(search_url, params=params, timeout=15)
            if response.status_code != 200:
                print(f"NASA Search Failed: {response.status_code}")
                return []
            
            data = response.json()
            items = data.get('collection', {}).get('items', [])
            
            forbidden = ["interview", "talking", "host", "speaker", "presentation", "conference", "panel", "portrait", "face", "talking head", "narrator", "explaining", "scientist"]
            
            for item in items: 
                item_data = item.get('data', [{}])[0]
                nasa_id = item_data.get('nasa_id')
                title = item_data.get('title', '').lower()
                description = item_data.get('description', '').lower()
                keywords = [k.lower() for k in item_data.get('keywords', [])]
                
                # Check for forbidden terms in title, description, or keywords
                if any(f in title for f in forbidden) or any(f in description for f in forbidden) or any(any(f in k for f in forbidden) for k in keywords):
                    # print(f"Skipping NASA video {nasa_id} due to human-centric content.")
                    continue
                
                # Prioritize mission-based results if they look purely scientific
                # (e.g., if it has 'Hubble' and not 'person' it's likely a B-roll)

                # The 'href' in the item points to a list of media assets
                asset_manifest_url = item.get('href')
                
                if asset_manifest_url:
                    video_url = self._get_best_mp4_from_manifest(asset_manifest_url)
                    if video_url:
                        filename = f"nasa_{nasa_id}_{int(time.time())}.mp4"
                        path = self._download_video(video_url, filename)
                        if path:
                            paths.append(path)
                        
                if len(paths) >= count:
                    break
        except Exception as e:
            print(f"NASA Fetcher Error: {e}")
            
        return paths

    def _get_best_mp4_from_manifest(self, manifest_url: str) -> str:
        try:
            resp = requests.get(manifest_url, timeout=10)
            if resp.status_code == 200:
                assets = resp.json()
                # NASA asset manifest is a list of direct URLs
                # Filter for .mp4 and prioritize ~orig.mp4 or ~mobile.mp4 for size/speed
                mp4s = [a for a in assets if isinstance(a, str) and a.endswith('.mp4')]
                
                # Priority: medium bitrate usually has 'medium', then 'mobile', then 'orig'
                for kw in ['medium', 'small', 'mobile', 'orig']:
                    for url in mp4s:
                        if kw in url.lower():
                            return url
                
                if mp4s: return mp4s[0]
        except:
            pass
        return None

    def _download_video(self, url: str, filename: str) -> str:
        save_path = os.path.join(self.download_dir, filename)
        try:
            # Check size first if possible? NASA servers are usually fast.
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if os.path.exists(save_path) and os.path.getsize(save_path) > 10000:
                    return save_path
        except Exception as e:
            print(f"NASA Download Failed for {url}: {e}")
        return None
