import os
import requests
from duckduckgo_search import DDGS
import random
import time

class ImageFetcher:
    def __init__(self, download_dir="storage/temp_images"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_multi_images(self, queries: list, base_filename: str) -> list:
        """ 
        Fetches multiple images by performing fewer, broader searches.
        This reduces the risk of hitting DDG rate limits.
        """
        paths = []
        # Use only a subset of unique/important queries to reduce search count
        unique_queries = list(dict.fromkeys(queries)) # preserve order
        
        images_needed = len(queries)
        # We try to get about 4 images per search result set to minimize queries
        images_per_search = 4 if len(unique_queries) > 1 else images_needed
        
        for i, q in enumerate(unique_queries[:3]): # Max 3 global searches per news item
            # Add photographic context to the query if it doesn't have it
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
            time.sleep(2) # Cooldown between searches
            
        return paths

    def _search_ddg(self, query: str, max_results: int = 20) -> list:
        """ Internal helper for DDG image search. """
        # Construct a specific news query to avoid diagrams
        search_query = f"{query} -diagram -chart -graph -map -vector"
        
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
                
                # Filter results for valid extensions and exclude common non-photo patterns
                forbidden = ["diagram", "chart", "graph", "vector", "drawing", "illustration", "map", "infographic", "logo"]
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
        """ Internal helper to download an image with size validation. """
        # Sanitize filename
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            if response.status_code == 200 and len(response.content) > 50000: # 50KB min
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return save_path
        except:
            pass
        return None

    def fetch_image(self, query: str, filename: str) -> str:
        """ Legacy wrapper for single image fetch. """
        results = self._search_ddg(query)
        for url in results:
            path = self._download_image(url, filename)
            if path: return path
        return None

if __name__ == "__main__":
    fetcher = ImageFetcher()
    fetcher.fetch_multi_images(["Japan Earthquake", "Tsunami"], "test_fetch")
