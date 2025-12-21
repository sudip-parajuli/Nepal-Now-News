import os
import requests
from duckduckgo_search import DDGS
import random
import time

class ImageFetcher:
    def __init__(self, download_dir="automation/storage/temp_images"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_multi_images(self, queries: list, base_filename: str) -> list:
        paths = []
        # Flatten and deduplicate queries
        flat_queries = []
        for q in queries:
            if isinstance(q, list): flat_queries.extend(q)
            else: flat_queries.append(q)
        unique_queries = list(dict.fromkeys(flat_queries))
        images_needed = len(queries)
        images_per_search = 4 if len(unique_queries) > 1 else images_needed
        
        for i, q in enumerate(unique_queries[:3]):
            refined_q = q if "photo" in q.lower() else f"{q} news photo"
            print(f"Searching images for: {refined_q}...")
            results = self._search_ddg(refined_q, max_results=15)
            
            if results:
                count = 0
                for img_url in results:
                    filename = f"{base_filename}_{len(paths)}.jpg"
                    path = self._download_image(img_url, filename)
                    if path:
                        paths.append(path)
                        count += 1
                    if count >= images_per_search or len(paths) >= images_needed:
                        break
            
            if len(paths) >= images_needed:
                break
            time.sleep(2)
            
        return paths

    def _search_ddg(self, query: str, max_results: int = 20) -> list:
        # Exclude diagrams, text, bottles, and products for professional look
        search_query = f"{query} -diagram -chart -graph -map -vector -text -bottle -label -product -person -face -human -interview -talking"
        try:
            with DDGS() as ddgs:
                results = ddgs.images(
                    keywords=search_query,
                    region="wt-wt",
                    safesearch="on",
                    size="large",
                    type_image="photo"
                )
                if not results: return []
                forbidden = ["diagram", "chart", "graph", "vector", "drawing", "illustration", "map", "infographic", "logo", "person", "face", "human", "interview", "talking"]
                filtered = []
                for r in results:
                    url = r['image'].lower()
                    title = r.get('title', '').lower()
                    if any(f in url for f in forbidden) or any(f in title for f in forbidden):
                        continue
                    if url.split('.')[-1] in ['jpg', 'jpeg', 'png', 'webp']:
                        filtered.append(r['image'])
                random.shuffle(filtered)
                return filtered[:max_results]
        except Exception as e:
            print(f"DDG Search error for '{query}': {e}")
            return []

    def _download_image(self, url: str, filename: str) -> str:
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) UserAgent'}
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code == 200 and len(response.content) > 5000:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return save_path
        except:
            pass
        return None

    def fetch_image(self, query: str, filename: str) -> str:
        results = self._search_ddg(query)
        for url in results:
            path = self._download_image(url, filename)
            if path: return path
        return None
