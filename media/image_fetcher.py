import os
import requests
from duckduckgo_search import DDGS
import random

class ImageFetcher:
    def __init__(self, download_dir="storage/temp_images"):
        self.download_dir = download_dir
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)

    def fetch_multi_images(self, queries: list, base_filename: str) -> list:
        """ Fetches multiple images based on a list of queries with a small delay. """
        paths = []
        for i, q in enumerate(queries):
            path = self.fetch_image(q, f"{base_filename}_{i}.jpg")
            if path:
                paths.append(path)
            if i < len(queries) - 1:
                time.sleep(1.5) # Add jitter/delay to avoid ratelimit
        return paths

    def fetch_image(self, query: str, filename: str) -> str:
        """
        Searches and downloads a relevant image from DuckDuckGo.
        Returns the path to the downloaded image.
        """
        # Sanitize filename
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        
        # KEYWORD EXTRACTION: DuckDuckGo hates long queries. 
        # Extract the most 'meaningful' words or just the first few nouns/keywords.
        words = [w for w in query.split() if len(w) > 3] # Filter out short words
        if len(words) > 4:
            search_query = " ".join(words[:4]) # Only use first 4 keywords
        else:
            search_query = " ".join(words)
            
        print(f"Searching images for: {search_query}")
        
        try:
            with DDGS() as ddgs:
                results = ddgs.images(
                    keywords=search_query,
                    region="wt-wt",
                    safesearch="on",
                    size="large"
                )
                
                if not results:
                    print(f"No results for: {search_query}")
                    return None

                # Shuffle to get variety
                image_urls = [r['image'] for r in results if r['image'].split('.')[-1].lower() in ['jpg', 'jpeg', 'png']]
                random.shuffle(image_urls)

                for url in image_urls[:5]:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                        response = requests.get(url, timeout=8, headers=headers)
                        if response.status_code == 200:
                            with open(save_path, 'wb') as f:
                                f.write(response.content)
                            return save_path
                        elif response.status_code == 202 or response.status_code == 403:
                            print(f"Image host {url} returned {response.status_code}. Skipping.")
                    except:
                        continue
        except Exception as e:
            print(f"DDG Search error: {e}")
            
        return None

if __name__ == "__main__":
    fetcher = ImageFetcher()
    fetcher.fetch_image("Japan Earthquake", "test_japan.jpg")
