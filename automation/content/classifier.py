from typing import List, Dict

class NewsClassifier:
    BREAKING_KEYWORDS = [
        "breaking", "live", "alert", "emergency",
        "explosion", "earthquake", "crash", "attack", 
        "deadly", "shooting", "urgent", "tsunami", "nuclear", "flash",
        "ब्रेकिङ", "अपडेट", "घटना", "मृत्यु", 
        "घाइते", "विस्फोट", "भूकम्प", "आक्रमण", "फैसला", "जरुरी", "तत्काल", "खतरा", "अवरुद्ध"
    ]

    def __init__(self, breaking_window_hours: int = 2):
        self.breaking_window_hours = breaking_window_hours

    def classify(self, news_item: Dict) -> str:
        headline = news_item.get('headline', '').lower()
        is_urgent = any(kw in headline for kw in self.BREAKING_KEYWORDS)
        if is_urgent:
            return "BREAKING"
        return "NORMAL"

    def filter_breaking(self, news_items: List[Dict]) -> List[Dict]:
        return [item for item in news_items if self.classify(item) == "BREAKING"]
