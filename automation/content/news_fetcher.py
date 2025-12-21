import feedparser
import hashlib
from typing import List, Dict

class RSSFetcher:
    def __init__(self, feeds: List[str]):
        self.feeds = feeds

    def fetch_all(self) -> List[Dict]:
        all_news = []
        for url in self.feeds:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    headline = entry.get("title", "")
                    news_item = {
                        "headline": headline,
                        "content": entry.get("summary", "") or entry.get("description", ""),
                        "source": url,
                        "published_time": entry.get("published", ""),
                        "url": entry.get("link", "")
                    }
                    news_item["hash"] = self._generate_hash(news_item)
                    news_item["headline_hash"] = self._generate_headline_hash(headline)
                    all_news.append(news_item)
            except Exception as e:
                print(f"Error fetching {url}: {e}")
        return all_news

    def _generate_hash(self, item: Dict) -> str:
        content = f"{item['headline']}{item['content']}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _generate_headline_hash(self, headline: str) -> str:
        normalized = self._normalize_headline(headline)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def _normalize_headline(self, headline: str) -> str:
        # Lowercase, remove extra spaces, remove common prefixes
        h = headline.lower().strip()
        # Remove anything in brackets
        import re
        h = re.sub(r'\[.*?\]', '', h)
        h = re.sub(r'\(.*?\)', '', h)
        # Remove common separators
        h = re.sub(r'[:|]', ' ', h)
        # Remove extra whitespace
        h = " ".join(h.split())
        return h
