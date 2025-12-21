import os
from automation.media.video_fetcher import VideoFetcher
from automation.media.image_fetcher import ImageFetcher

def test_search_queries():
    print("Testing Video Search Query...")
    vf = VideoFetcher()
    # Intercept print to check query
    # In reality, we just run it and see the output in console
    vf.fetch_stock_videos("black hole", count=1)
    
    print("\nTesting Image Search Query...")
    ifObj = ImageFetcher()
    # _search_ddg is internal but we can check its query formation by looking at code or behavior
    ifObj.fetch_multi_images(["nebula"], "test_filter")

if __name__ == "__main__":
    test_search_queries()
