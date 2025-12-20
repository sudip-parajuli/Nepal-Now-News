import asyncio
from automation.media.nasa_fetcher import NASAFetcher

async def test_nasa():
    fetcher = NASAFetcher("automation/storage/test_nasa")
    print("Testing NASA Search for 'Mars Perseverance'...")
    paths = fetcher.fetch_nasa_videos("Mars Perseverance", count=1)
    if paths:
        print(f"SUCCESS: Downloaded {len(paths)} videos.")
        print(f"Path: {paths[0]}")
    else:
        print("FAILED: No videos found or downloaded.")

if __name__ == "__main__":
    asyncio.run(test_nasa())
