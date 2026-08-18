import json
import os
import random
import re
from collections import Counter
from typing import List

from .script_writer import is_llm_failure

class ScienceTopicGenerator:
    def __init__(self, history_file: str, topics: List[str]):
        self.history_file = history_file
        self.topics = topics
        # Category rotation state lives next to the history file.
        self.queue_file = os.path.join(
            os.path.dirname(history_file) or ".", "category_queue.json"
        )
        self.history = self._load_history()
        self.category_queue = self._load_queue()

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

    def _load_queue(self) -> List[str]:
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    q = json.load(f)
                    if isinstance(q, list) and q and all(t in self.topics for t in q):
                        return q
            except: pass
        return []

    def _save_queue(self):
        os.makedirs(os.path.dirname(self.queue_file) or ".", exist_ok=True)
        with open(self.queue_file, 'w', encoding='utf-8') as f:
            json.dump(self.category_queue, f)

    def _next_category(self) -> str:
        """
        Round-robin through every category before any repeat, instead of random.choice()
        on each run. With a short, astronomy-heavy topic list, pure random selection meant
        the same 2-3 categories dominated by chance alone — a big part of why the channel's
        output has been so repetitive. Shuffling one full pass through all categories
        guarantees every field of science gets covered before anything repeats.
        """
        if not self.category_queue:
            self.category_queue = list(self.topics)
            random.shuffle(self.category_queue)
        category = self.category_queue.pop(0)
        self._save_queue()
        return category

    @staticmethod
    def _normalize(s: str) -> str:
        return re.sub(r'[^a-z0-9 ]', '', s.lower()).strip()

    def _overused_terms(self, sample_size: int = 150, top_n: int = 12, min_count: int = 4) -> List[str]:
        """Surfaces words that keep showing up across recent sub-topics (e.g. 'bioluminescent',
        'gravitational', 'attractor') so the prompt can explicitly steer away from them, on top
        of the plain duplicate check."""
        stop = {
            'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'and', 'or',
            'is', 'are', 'with', 'from', 'that', 'this', 'its', "s",
        }
        counter = Counter()
        for text in self.history[-sample_size:]:
            for w in re.findall(r"[a-zA-Z']+", text.lower()):
                if len(w) > 4 and w not in stop:
                    counter[w] += 1
        return [w for w, c in counter.most_common(top_n) if c >= min_count]

    def get_next_topic(self, script_writer) -> str:
        """
        Selects a category (round-robin) and generates a specific sub-topic using LLM.
        """
        category = self._next_category()

        recent = self.history[-30:]
        overused = self._overused_terms()

        prompt = f"""
        Generate a fascinating, specific, and scientifically accurate sub-topic for a YouTube video about {category}.
        Example for 'Space & Astronomy': 'The Diamond Planet 55 Cancri e' or 'The sound of a black hole'.
        Example for 'Ocean & Marine Life': 'The Mariana Trench life forms'.
        Example for 'Human Biology & Anatomy': 'Why your gut has its own nervous system'.

        Rules:
        - Must be mind-blowing and true.
        - Must be genuinely different from these recently used sub-topics (no repeats, no close
          variations of the same idea): {", ".join(recent) if recent else "none yet"}
        - This channel has already covered these angles far too many times — pick something that
          does NOT center on: {", ".join(overused) if overused else "nothing yet"}.
        - Output ONLY the sub-topic name (3-6 words).
        """

        sub_topic = ""
        seen_normalized = {self._normalize(h) for h in self.history}
        for attempt in range(2):
            candidate = script_writer._call_with_retry(prompt)
            candidate = candidate.replace('"', '').strip()
            # A total LLM outage (every Gemini key + every Groq fallback failing) must
            # never flow downstream as if it were a real topic — a past incident let the
            # literal failure-sentinel string get used as the video's topic/title, and its
            # narration was the TTS reading out the error message on a published video.
            # Fail the whole pipeline run loudly instead (no upload happens) so a
            # provider-side outage shows up as a failed CI run, not a live broken video.
            if is_llm_failure(candidate):
                raise RuntimeError(
                    "ScienceTopicGenerator: LLM topic generation failed on every "
                    "Gemini key and every Groq fallback — aborting rather than "
                    "publishing the error as content. Check API keys/quotas/model "
                    "availability."
                )
            sub_topic = candidate
            if self._normalize(candidate) not in seen_normalized:
                break
            print(f"[ScienceTopicGenerator] Duplicate sub-topic '{candidate}' detected, retrying...")

        self.history.append(sub_topic)
        self._save_history()
        return sub_topic
