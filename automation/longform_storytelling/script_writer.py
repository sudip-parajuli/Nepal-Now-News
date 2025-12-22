import os
import re
from typing import List, Dict
from google import genai
from google.genai import types
from groq import Groq

class ScriptWriter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-2.0-flash-exp"
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None

    def generate_story_script(self, topic_title: str) -> List[Dict]:
        """
        Generates a dialogue script between Baje and Arav.
        """
        prompt = f"""
Write a humorous and warm Nepali dialogue script for a YouTube video series "बाजे र Gen-Z — हल्का गफ, गहिरो कुरा".
Topic: {topic_title}

Characters:
1. बाजे (Baje): 60-70 years old, witty, wise, uses traditional Nepali proverbs (उखान टुक्का), warm but slightly sarcastic.
2. आरव (Arav): 20-25 years old Gen-Z, curious, playful, uses modern Nepali slang mixed with English tech/social media terms where natural.

Language Constraints:
- CRITICAL: Use PURE NEPALI vocabulary. Avoid Hindi words that are often confused with Nepali (e.g., use 'खुसी' not 'खुश', 'सुरु' not 'शुरु', 'प्रयास' not 'कोशिश', 'समय' not 'वक्त').
- ACCENT: Ensure the dialogue reflects authentic Nepali sentence structures and local flavor.
- GRAMMAR: Follow standard Nepali grammar rules strictly.
- ENGLISH: Use English words only for Arav when referring to modern concepts (e.g., 'vibe', 'trending', 'social media'). Ensure they are spelled correctly in English within the Devanagari script if common, or keep them as English characters if they are technical terms.
- Tone: Light, conversational, village-veranda-style "गफ".
- NO preaching, NO news, NO politics.
- MANDATORY: Start with a strong hook in the first 10-15 seconds (e.g., a funny contrast or a provocative question).
- FORMAT: Each line MUST start with the character name and include an [Emotion Tag] followed by a colon.

Example Format:
बाजे [Smiling]: ओए आरव, आजकलको यो 'Online' माया भन्दा त हाम्रै घाँस काट्दा भेटेको माया गाढा हुन्थ्यो नि!
आरव [Amused]: बाजे, तपाईँ त फेरि कुरै नबुझी 'Cancel' गर्न खोज्नु भो त! अचेल त 'Vibe' मिलेपछि माया बस्छ।

Write the full script now.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.9,
                )
            )
            script_text = response.text
        except Exception as e:
            print(f"Gemini Error: {e}. Attempting Groq fallback...")
            if self.groq_client:
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.3-70b-versatile",
                    )
                    script_text = chat_completion.choices[0].message.content
                except Exception as ge:
                    print(f"Groq Error: {ge}")
                    return []
            else:
                return []
        
        return self._parse_script(script_text)

    def _parse_script(self, text: str) -> List[Dict]:
        lines = []
        # Pattern to match: Character [Emotion]: Dialogue
        pattern = r"(बाजे|आरव)\s*\[(.*?)\]\s*:\s*(.*)"
        
        for line in text.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                speaker = match.group(1)
                emotion = match.group(2)
                dialogue = match.group(3)
                lines.append({
                    "speaker": speaker,
                    "emotion": emotion,
                    "text": dialogue
                })
        
        return lines

if __name__ == "__main__":
    # Test script writer
    writer = ScriptWriter(os.getenv("GEMINI_API_KEY"))
    script = writer.generate_story_script("Mobile addiction and screen time")
    for line in script[:5]:
        print(f"{line['speaker']} ({line['emotion']}): {line['text']}")
