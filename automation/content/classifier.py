from typing import List, Dict

class NewsClassifier:
    BREAKING_KEYWORDS = [
        "ताजा खबर", "ब्रेकिङ न्युज", "विशेष समाचार", "मुख्य समाचार", "महत्वपूर्ण अपडेट",
        "ताजा समाचार", "ताजा अपडेट", "लाइभ अपडेट", "तत्काल", "अहिले भर्खरै", "अलर्ट", "चेतावनी",
        "दुर्घटना", "भूकम्प", "बाढी", "पहिरो", "आगोलागी", "मौसम",
        "पक्राउ", "तस्करी", "शंकास्पद वस्तु", "आक्रमण", "हमला", "हवाई आक्रमण", "बम विष्फोट", 
        "गोलाबारी", "आत्माघाती आक्रमण", "सैन्य कारबाही", "धावा",
        "सुनको भाउ", "शेयर बजार", "नेप्से", "अमेरिकी डलर", "अर्थतन्त्र", "बजेट", "विदेशी मुद्रा", "रेमिट्यान्स",
        "निर्वाचन", "मन्त्रिपरिषद्", "प्रतिनिधिसभा", "गठबन्धन", "राजनीति", "विधेयक", "संसद्", 
        "प्रधानमन्त्री", "राजीनामा", "निर्णय", "आन्दोलन", "हड्ताल",
        "खेलकुद", "क्रिकेट", "फुटबल",
        "स्वास्थ्य", "वैदेशिक रोजगार", "पर्यटन"
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
