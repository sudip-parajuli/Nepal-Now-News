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
        images_per_search = 3 if len(unique_queries) > 1 else images_needed
        
        for i, q in enumerate(unique_queries[:3]): # Max 3 searches per news item
            # Add photographic context to the query if it doesn't have it
            refined_q = q if "photo" in q.lower() else f"{q} news photo"
            results = self._search_ddg(refined_q, max_results=10)
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

    def fetch_image(self, query: str, filename: str) -> str:
        """
        Searches and downloads a relevant image from DuckDuckGo.
        Returns the path to the downloaded image.
        """
        # Sanitize filename
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        
        # KEYWORD EXTRACTION & CONTEXT FILTERING
        # Avoid generic terms that trigger "Diagrams"
        stop_words = ["decision", "system", "program", "random", "process", "rule"]
        query_words = query.lower().split()
        
        # If the query is mostly "stop words", try using the first few words but force "Photo" and "News"
        search_terms = [w for w in query_words if len(w) > 3]
        
        # Construct a very specific news query
        # We append negative terms to avoid diagrams/charts
        # AND we force photographic context
        if len(search_terms) > 5:
            base_query = " ".join(search_terms[:5])
        else:
            base_query = " ".join(search_terms)
            
        search_query = f"{base_query} news photo -diagram -chart -graph -map -decision-tree -vector"
        
        print(f"Refined search: {search_query}")
        
        try:
            with DDGS() as ddgs:
                results = ddgs.images(
                    keywords=search_query,
                    region="wt-wt",
                    safesearch="on",
                    size="large",
                    type_image="photo" # EXPLICITLY ask for photos
                )
                
                if not results:
                    return None

                # Strict Filtering: Exclude anything that looks like a diagram/vector
                forbidden = ["diagram", "chart", "graph", "vector", "drawing", "illustration", "map", "infographic", "logo"]
                
                filtered_results = []
                for r in results:
                    url = r['image'].lower()
                    title = r.get('title', '').lower()
                    
                    if any(f in url for f in forbidden) or any(f in title for f in forbidden):
                        continue
                        
                    if url.split('.')[-1] in ['jpg', 'jpeg', 'png']:
                        filtered_results.append(r['image'])

                if not filtered_results:
                    print(f"No specific photos found for: {base_query}. Trying general news fallback.")
                    # Fallback to generic news aesthetic if story-specific search is too restrictive
                    fallback_results = ddgs.images(
                        keywords="breaking news world report photo -diagram",
                        size="large",
                        type_image="photo"
                    )
                    filtered_results = [r['image'] for r in fallback_results if r['image'].split('.')[-1].lower() in ['jpg', 'jpeg', 'png']]

                if not filtered_results:
                    return None

                random.shuffle(filtered_results)

                for url in filtered_results[:12]:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                        response = requests.get(url, timeout=10, headers=headers)
                        if response.status_code == 200:
                            # Strict size check: Ensure it's not a small icon/diagram
                            if len(response.content) > 60000: # 60KB min
                                with open(save_path, 'wb') as f:
                                    f.write(response.content)
                                return save_path
                    except Exception as e:
                        continue
        except Exception as e:
            print(f"DDG Search error: {e}")
            
        return None

if __name__ == "__main__":
    fetcher = ImageFetcher()
    fetcher.fetch_image("Japan Earthquake", "test_japan.jpg")
