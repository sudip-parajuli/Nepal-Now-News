from typing import List, Dict

class NewsClassifier:
    BREAKING_KEYWORDS = [
        "आक्रमण", "दुर्घटना", "युद्ध", "हत्या", "मृत्यु", "विजय", "हार", "मूल्य वृद्धि",
        "ब्रेकिङ न्युज", "विशेष समाचार", "महत्वपूर्ण अपडेट",
        "लाइभ अपडेट", "तत्काल", "अहिले भर्खरै", "अलर्ट", "चेतावनी",
        "भूकम्प", "बाढी", "पहिरो", "आगोलागी", "मौसम",
        "पक्राउ", "तस्करी", "शंकास्पद वस्तु", "बम विष्फोट", 
        "गोलाबारी", "आत्माघाती आक्रमण", "सैन्य कारबाही", "धावा",
        # Financial/Sports/Election removed to prevent routine news spam
        "राजीनामा", "आन्दोलन", "हड्ताल"
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
