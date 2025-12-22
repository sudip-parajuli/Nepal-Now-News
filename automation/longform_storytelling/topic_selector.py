import json
import os
import random
from typing import List, Dict

class TopicSelector:
    TOPICS = [
        {"id": "stress", "title": "Stress: then vs now", "weight": 1.0},
        {"id": "mobile_addiction", "title": "Mobile addiction and screen time", "weight": 1.2},
        {"id": "education_pressure", "title": "Education pressure and results", "weight": 1.0},
        {"id": "foreign_employment", "title": "Foreign employment dreams", "weight": 1.1},
        {"id": "inflation", "title": "महँगाइ (Inflation) and daily life", "weight": 1.3},
        {"id": "patience", "title": "Patience vs instant results", "weight": 0.9},
        {"id": "community", "title": "Social media vs real community", "weight": 1.0},
        {"id": "traditional_festivals", "title": "Traditional festivals then vs now", "weight": 0.8},
        {"id": "transportation", "title": "Walking vs Pathao/InDrive culture", "weight": 1.1},
        {"id": "food_habits", "title": "Gundruk-Dhido vs Burger-Pizza", "weight": 1.2},
    ]

    def __init__(self, history_file: str = "automation/storage/topic_history.json", cooldown: int = 5):
        self.history_file = history_file
        self.cooldown = cooldown
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, 'w') as f:
                json.dump([], f)

    def _load_history(self) -> List[str]:
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except:
            return []

    def _save_history(self, history: List[str]):
        with open(self.history_file, 'w') as f:
            json.dump(history[-20:], f)

    def select_topic(self) -> Dict:
        history = self._load_history()
        
        # Filter out topics in cooldown
        available_topics = [t for t in self.TOPICS if t['id'] not in history[-self.cooldown:]]
        
        if not available_topics:
            available_topics = self.TOPICS # Reset if all are in cooldown

        # Weighted selection
        weights = [t['weight'] for t in available_topics]
        selected = random.choices(available_topics, weights=weights, k=1)[0]
        
        # Update history
        history.append(selected['id'])
        self._save_history(history)
        
        return selected

if __name__ == "__main__":
    selector = TopicSelector()
    topic = selector.select_topic()
    print(f"Selected Topic: {topic['title']} (ID: {topic['id']})")
