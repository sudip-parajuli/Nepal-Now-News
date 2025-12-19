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
        """ Fetches multiple images based on a list of queries. """
        paths = []
        for i, q in enumerate(queries):
            path = self.fetch_image(q, f"{base_filename}_{i}.jpg")
            if path:
                paths.append(path)
        return paths

    def fetch_image(self, query: str, filename: str) -> str:
        """
        Searches and downloads a relevant image from DuckDuckGo.
        Returns the path to the downloaded image.
        """
        # Sanitize filename (remove spaces, parentheses)
        filename = "".join([c if c.isalnum() or c in "._-" else "_" for c in filename])
        save_path = os.path.join(self.download_dir, filename)
        
        # Clean query: focus on keywords
        words = query.split()
        if len(words) > 8:
            search_query = " ".join(words[:8])
        else:
            search_query = query
            
        search_query = f"{search_query} international news"
        
        try:
            with DDGS() as ddgs:
                results = ddgs.images(
                    keywords=search_query,
                    region="wt-wt",
                    safesearch="on",
                    size="large"
                )
                
                # Filter results for common image extensions
                image_urls = [r['image'] for r in results if r['image'].split('.')[-1].lower() in ['jpg', 'jpeg', 'png']]
                
                if not image_urls:
                    print(f"No images found for query: {query}")
                    return None

                # Shuffle to get different images each time
                random.shuffle(image_urls)

                # Try the first few results until one succeeds
                for url in image_urls[:10]:
                    try:
                        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                        response = requests.get(url, timeout=10, headers=headers)
                        if response.status_code == 200:
                            with open(save_path, 'wb') as f:
                                f.write(response.content)
                            print(f"Downloaded image: {save_path}")
                            return save_path
                    except Exception as e:
                        print(f"Failed to download image from {url}: {e}")
        except Exception as e:
            print(f"Image search failed for {query}: {e}")
            
        return None

if __name__ == "__main__":
    fetcher = ImageFetcher()
    fetcher.fetch_image("Japan Earthquake", "test_japan.jpg")
