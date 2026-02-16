from automation.media.image_fetcher import ImageFetcher
import os

def test_fetch():
    print("Testing ImageFetcher...")
    fetcher = ImageFetcher()
    
    query = "galaxy 4k cinematic"
    try:
        paths = fetcher.fetch_multi_images([query], "test_img_valid")
        print(f"Fetched {len(paths)} images.")
        for p in paths:
            print(f" - {p}")
            
    except Exception as e:
        print(f"Fetch failed: {e}")

if __name__ == "__main__":
    test_fetch()
