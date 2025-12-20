import json
import os
from datetime import datetime, timedelta

class NewsClassifier:
    BREAKING_KEYWORDS = [
        "breaking", "live", "alert", "emergency", "update", 
        "explosion", "earthquake", "crash", "attack", "decision", 
        "deadly", "shooting", "urgent", "tsunami", "nuclear", "flash",
        "ब्रेकिङ", "ताजा", "विशेष", "अपडेट", "घटना", "मृत्यु", 
        "घाइते", "विस्फोट", "भूकम्प", "आक्रमण", "फैसला", "जरुरी",
        "प्रमुख", "खबर", "समाचार", "तत्काल", "खतरा", "अवरुद्ध", "पक्राउ"
    ]

    def __init__(self, breaking_window_hours: int = 2):
        self.breaking_window_hours = breaking_window_hours

    def classify(self, news_item: dict) -> str:
        """
        Classifies news item as BREAKING or NORMAL.
        """
        is_urgent = any(kw in news_item['headline'].lower() for kw in self.BREAKING_KEYWORDS)
        
        # Check time recency (approximate if published_time is just a string)
        # For simplicity in this step, we mainly rely on keywords if timestamp is hard to parse
        # But we can try to parse it if needed.
        
        if is_urgent:
            return "BREAKING"
        return "NORMAL"

    def filter_breaking(self, news_items: list) -> list:
        return [item for item in news_items if self.classify(item) == "BREAKING"]

if __name__ == "__main__":
    sample = {
        "headline": "BREAKING: Massive earthquake hits Japan",
        "content": "A 7.5 magnitude earthquake struck northern Japan...",
        "source": "BBC",
        "published_time": "2025-12-19T10:00:00Z"
    }
    classifier = NewsClassifier()
    print(f"Classification: {classifier.classify(sample)}")
