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

    def fetch_multi_images(self, queries: list, base_filename: str, topic_context: str = None) -> list:
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

    def _search_ddg(self, query: str, max_results: int = 20, topic_context: str = None) -> list:
        # Exclude diagrams, text, and people for professional science look
        negative_filters = "-person -face -human -man -woman -portrait -interview -talking -host -adult -child -people -diagram -chart -graph -map -vector -text -logo"
        
        if topic_context:
            is_science = any(tw in topic_context.lower() for tw in ["space", "universe", "galaxy", "ocean", "science", "nature"])
            quality_boost = "4K cinematic " if is_science else ""
            search_query = f"{topic_context} {query} {quality_boost}{negative_filters}"
        else:
            search_query = f"{query} {negative_filters}"
            
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = ddgs.images(
                        keywords=search_query,
                        region="wt-wt",
                        safesearch="on",
                        size="large",
                        type_image="photo"
                    )
                    if results:
                        forbidden = ["diagram", "chart", "graph", "vector", "drawing", "illustration", "map", "infographic", "logo", "person", "face", "human", "man", "woman", "interview", "talking", "portrait"]
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
                print(f"DDG Search error for '{query}' (Attempt {attempt+1}/3): {e}")
                # Retry on almost any error since DDG is flaky
                time.sleep(5 * (attempt + 1)) 
                continue
        
        # Fallback to Wikimedia
        print(f"DDG failed for '{query}'. Trying Wikimedia Fallback...")
        return self._search_wikimedia(query, max_results)

    def _search_wikimedia(self, query: str, max_results: int = 20) -> list:
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrnamespace": 6, # File namespace
                "gsrsearch": f"filetype:bitmap|drawing -person -portrait {query}",
                "gsrlimit": max_results * 2,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata",
            }
            headers = {'User-Agent': 'NepalNowBot/1.0 (contact@example.com)'}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            image_urls = []
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if "imageinfo" in page:
                    img_url = page["imageinfo"][0]["url"]
                    if img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        image_urls.append(img_url)
            
            random.shuffle(image_urls)
            print(f"Wikimedia found {len(image_urls)} images for '{query}'.")
            return image_urls[:max_results]
        except Exception as e:
            print(f"Wikimedia Search Error: {e}")
            return []

    def _download_image(self, url: str, filename: str) -> str:
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) UserAgent'}
            response = requests.get(url, timeout=15, headers=headers)
            if response.status_code == 200 and len(response.content) > 1000: # Lowered min size slightly
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                # VALIDATE IMAGE
                try:
                    from PIL import Image
                    with Image.open(save_path) as img:
                        img.verify() # Check for corruption
                    return save_path
                except Exception as e:
                    print(f"Invalid image downloaded ({url}): {e}")
                    os.remove(save_path)
                    return None
        except Exception as e:
            print(f"Download Error ({url}): {e}")
        return None

    def fetch_image(self, query: str, filename: str) -> str:
        # Hybrid search
        results = self._search_ddg(query)
        # If DDG fails (and returns empty despite fallback logic above, which shouldn't happen but safe to keep)
        if not results:
             results = self._search_wikimedia(query)

        for url in results:
            path = self._download_image(url, filename)
            if path: return path
        return None
