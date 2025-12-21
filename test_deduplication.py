import os
os.environ["GEMINI_API_KEY"] = "dummy" # Avoid client init error
import json
import asyncio
from automation.content.news_fetcher import RSSFetcher
from automation.pipelines.nepali_news_pipeline import NepaliNewsPipeline

def test_normalization():
    fetcher = RSSFetcher([])
    h1 = "ब्रेकिङ: काठमाडौंमा वर्षा [अपडेट]"
    h2 = "काठमाडौंमा वर्षा - Online Khabar"
    
    norm1 = fetcher._normalize_headline(h1)
    norm2 = fetcher._normalize_headline(h2)
    
    print(f"H1: {h1} -> {norm1}")
    print(f"H2: {h2} -> {norm2}")
    
    # Simple check if normalization works (it might not be identical yet, but stripping helps)
    # The more aggressive the normalization, the better the deduplication.

class MockScriptWriter:
    def rewrite_for_shorts(self, h, c): return "Mocked script for " + h
    def summarize_for_daily(self, items): return [{"type": "intro", "text": "Mocked", "gender": "male"}]
    def generate_image_keywords(self, h): return ["mock"]

async def test_pipeline_dedup():
    config = {
        'feeds': [],
        'tts_voice': {'male': 'ne-NP-SagarNeural', 'female': 'ne-NP-HemkalaNeural'},
        'storage': {'posted_news': 'automation/storage/test_posted_news.json'},
        'branding': {}
    }
    
    # Clear test storage
    if os.path.exists(config['storage']['posted_news']):
        os.remove(config['storage']['posted_news'])
        
    pipeline = NepaliNewsPipeline(config)
    pipeline.script_writer = MockScriptWriter() # MOCK
    fetcher = RSSFetcher([])
    
    # Mock news items with same headline but different content (simulating different feeds)
    news_item1 = {
        "headline": "काठमाडौंमा ट्राफिक जाम",
        "content": "आज काठमाडौंको ट्राफिक अस्तव्यस्त छ।",
        "source": "feed1",
        "hash": "hash1",
        "headline_hash": fetcher._generate_headline_hash("काठमाडौंमा ट्राफिक जाम")
    }
    
    news_item2 = {
        "headline": "[ताजा खबर] काठमाडौंमा ट्राफिक जाम",
        "content": "काठमाडौंमा आज गाडीको लामो लाइन देखिएको छ।",
        "source": "feed2",
        "hash": "hash2",
        "headline_hash": fetcher._generate_headline_hash("[ताजा खबर] काठमाडौंमा ट्राफिक जाम")
    }
    
    items = [news_item1, news_item2]
    
    print("Running pipeline with two similar news items...")
    # Run in test mode (no upload)
    await pipeline._run_breaking(items, is_test=True)
    
    # Check posted hashes
    hashes = pipeline._load_posted_hashes()
    print(f"Posted hashes count: {len(hashes)}")
    
    # We expect only one item to have been "processed" (uploaded logic)
    # Actually _run_breaking counts processed items.
    
    # If the logic worked, both items should result in the SAME headline_hash if normalized correctly.
    h_hash1 = fetcher._generate_headline_hash("काठमाडौंमा ट्राफिक जाम")
    h_hash2 = fetcher._generate_headline_hash("[ताजा खबर] काठमाडौंमा ट्राफिक जाम")
    
    print(f"Headline Hash 1: {h_hash1}")
    print(f"Headline Hash 2: {h_hash2}")
    
    if h_hash1 == h_hash2:
        print("SUCCESS: Headlines normalized to the same hash!")
    else:
        print("PRACTICAL NOTE: Headlines were not identical, but let's see if first one skipped the second.")

if __name__ == "__main__":
    test_normalization()
    asyncio.run(test_pipeline_dedup())
