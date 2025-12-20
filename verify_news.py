from fetchers.rss_fetcher import RSSFetcher
import asyncio

FEEDS = [
    "https://www.onlinekhabar.com/feed",
    "https://ratopati.com/feed",
    "https://setopati.com/feed",
    "https://www.bbc.com/nepali/index.xml",
    "https://myrepublica.nagariknetwork.com/feed",
    "https://thehimalayantimes.com/feed",
    "https://www.ronbpost.com/category/news/feed/"
]

def verify():
    print("--- Verifying News Feeds ---")
    fetcher = RSSFetcher(FEEDS)
    items = fetcher.fetch_all()
    print(f"Total items fetched: {len(items)}")
    
    sources = set([item['source'] for item in items])
    print(f"Fetched from {len(sources)} sources.")
    for s in sources:
        count = len([i for i in items if i['source'] == s])
        print(f" - {s}: {count} items")
    
    if items:
        print("\nSample Headline (Nepali):", items[0]['headline'])
        print("Sample Content Snippet:", items[0]['content'][:100])

if __name__ == "__main__":
    verify()
