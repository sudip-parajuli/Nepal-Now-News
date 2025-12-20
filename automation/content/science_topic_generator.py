import json
import os
import random
from typing import List

class ScienceTopicGenerator:
    def __init__(self, history_file: str, topics: List[str]):
        self.history_file = history_file
        self.topics = topics
        self.history = self._load_history()

    def _load_history(self) -> List[str]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: return []
        return []

    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)

    def get_next_topic(self, script_writer) -> str:
        """
        Selects a topic and generates a specific sub-topic using LLM.
        """
        category = random.choice(self.topics)
        
        prompt = f"""
        Generate a fascinating, specific, and scientifically accurate sub-topic for a 45-second YouTube Short about {category}.
        Example for 'Space': 'The Diamond Planet 55 Cancri e' or 'The sound of a black hole'.
        Example for 'Ocean': 'The Mariana Trench life forms'.
        
        Rules:
        - Must be mind-blowing and true.
        - Avoid repeating these previous topics: {", ".join(self.history[-10:])}
        - Output ONLY the sub-topic name (3-6 words).
        """
        
        sub_topic = script_writer._call_with_retry(prompt)
        # Clean sub_topic
        sub_topic = sub_topic.replace('"', '').strip()
        
        self.history.append(sub_topic)
        self._save_history()
        return sub_topic
