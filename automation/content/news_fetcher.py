"""
Grounds "breaking news" and "myth bust" social posts in real, recent articles instead
of pure LLM invention, using Google News RSS — free, no API key or signup required
(unlike NewsAPI.org, whose free tier's terms of service explicitly disallow use in a
live/production app like this one). This can't detect "what's trending on social media
right now" specifically (that needs a paid trends/social-listening API), but it does
surface real recent science journalism and fact-check coverage to write from.
"""
import html
import re
import feedparser

_RSS_BASE = "https://news.google.com/rss/search"


def fetch_recent_headlines(query: str, count: int = 5, when: str = "3d") -> list:
    """
    Returns up to `count` recent headlines matching `query` as
    [{"title": str, "summary": str, "source": str, "link": str}, ...].
    Returns [] on any failure (network, parse) — callers should fall back to
    LLM-only content generation rather than block on this.
    """
    try:
        import urllib.parse
        search_q = f"{query} when:{when}"
        params = urllib.parse.urlencode({"q": search_q, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        feed_url = f"{_RSS_BASE}?{params}"
        feed = feedparser.parse(feed_url)
        results = []
        for entry in feed.entries[:count]:
            source = ""
            if hasattr(entry, "source") and entry.source:
                source = html.unescape(entry.source.get("title", "")).strip()

            title = html.unescape(entry.get("title", "")).strip()
            # Google News titles are formatted "Headline - Source Name"; strip that
            # known trailing source suffix now that we have `source` separately.
            if source and title.endswith(f" - {source}"):
                title = title[: -(len(source) + 3)].strip()

            summary = re.sub(r'<[^>]+>', '', entry.get("summary", ""))
            summary = html.unescape(summary).strip()
            # The summary often just repeats "Headline  SourceName" with no real extra
            # detail — drop it when it's not adding anything beyond the title.
            if summary.replace(" ", "").startswith(title.replace(" ", "")[:40]):
                summary = ""

            if title:
                results.append({
                    "title": title,
                    "summary": summary[:300],
                    "source": source,
                    "link": entry.get("link", ""),
                })
        return results
    except Exception as e:
        print(f"[NewsFetcher] Failed to fetch headlines for '{query}': {e}")
        return []
