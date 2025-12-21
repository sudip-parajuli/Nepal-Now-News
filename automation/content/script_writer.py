from google import genai
from google.genai import errors
import os
import time
import random
import json
import re
from typing import List, Dict

class ScriptWriter:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-2.0-flash'
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except ImportError:
                self.groq_client = None
        else:
            self.groq_client = None

    def _call_with_retry(self, prompt: str, max_retries: int = 5) -> str:
        """Calls Gemini with exponential backoff, falling back to Groq if available."""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e:
                err_msg = str(e).lower()
                is_quota_error = "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg
                
                if is_quota_error and self.groq_client:
                    print(f"Gemini Quota Exceeded. Trying Groq fallback (Attempt {attempt+1})...")
                    try:
                        chat_completion = self.groq_client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        )
                        result = chat_completion.choices[0].message.content.strip()
                        if result: return result
                    except Exception as groq_err:
                        print(f"Groq fallback failed: {groq_err}")
                
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"LLM Error: {e}. Retrying in {wait_time:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"CRITICAL: LLM failed after {max_retries} attempts. Last error: {e}")
        
        return "Error: Maximum retries reached for LLM generation."

    def rewrite_for_shorts(self, headline: str, content: str) -> str:
        prompt = f"""
        Rewrite this breaking news into a 25–40 second YouTube Shorts script in Nepali.
        Headline: {headline}
        Content: {content}

        Language: Nepali (Devanagari script)
        Tone: Professional news anchor, formal, neutral.
        Rules:
        - Use standard Nepali news reporting grammar.
        - Ensure natural flow and correct tense usage.
        - RETURN ONLY THE NEPALI SPEECH TEXT. 
        - DO NOT include narrator labels.
        End with: 'थप अपडेटका लागि हामीसँगै रहनुहोला।'
        """
        script = self._call_with_retry(prompt)
        return self.clean_script(script)

    def generate_science_facts(self, topic: str) -> str:
        prompt = f"""
        Create an original educational YouTube Shorts script about "{topic}" in English.
        
        Requirements:
        - Language: English
        - Duration: 35-45 seconds of speech.
        - Tone: Calm, educational, documentary-style.
        - Structure:
            1. Hook: Start with a mind-blowing fact or intriguing question.
            2. Content: Explain 2-3 key scientific aspects clearly and engagingly.
            3. Engagement: END with a thought-provoking question for the audience to encourage comments and engagement.
        
        Rules:
        - Avoid clicks or exaggeration.
        - Be scientifically accurate.
        - RETURN ONLY THE ENGLISH SPEECH TEXT.
        - DO NOT include music cues or labels like [Narrator].
        """
        script = self._call_with_retry(prompt)
        return self.clean_script(script)

    def expand_science_script(self, topic: str, short_script: str = "") -> str:
        prompt = f"""
        Expand the following topic/short script into a detailed, high-quality documentary-style script for a 3-4 minute YouTube video.
        
        Topic: {topic}
        Current Short Script: {short_script}

        Requirements:
        - Language: English
        - Tone: Professional, authoritative, engaging (like Kurzgesagt or National Geographic).
        - Structure:
            1. Detailed Introduction: Set the stage and explain why this topic matters.
            2. Scientific Depth: Dive deep into the mechanics, history, and future implications.
            3. Multiple Perspectives: Mention different theories or recent discoveries.
            4. Conclusion: Summarize the profound impact of this scientific fact.
        
        Rules:
        - Maintain high scientific accuracy.
        - Use sophisticated yet accessible vocabulary.
        - RETURN ONLY THE SPEECH TEXT. No cues or labels.
        - Aim for approximately 400-600 words.
        """
        script = self._call_with_retry(prompt)
        return self.clean_script(script)

    def summarize_for_daily(self, news_items: List[Dict], channel_name: str = "Nepal Now") -> List[Dict]:
        news_text = "\n\n".join([f"Headline: {item['headline']}\nContent: {item['content']}" for item in news_items])
        prompt = f"""
        Summarize today's major news into a structured YouTube video script in Nepali for the channel "{channel_name}".
        
        News items:
        {news_text}

        Output Format: JSON list of objects.
        Structure sample:
        [
          {{"type": "intro", "text": "नमस्कार, {channel_name}मा हजुरलाइ स्वागत छ | आजको मुख्य समाचार यसप्रकार छन्", "gender": "female"}},
          {{"type": "news", "headline": "...", "text": "...", "gender": "male"}},
          {{"type": "outro", "text": "...", "gender": "male"}}
        ]

        Rules:
        - Alternate gender (male/female) for each news item.
        - Professional reporting style.
        - RETURN ONLY THE JSON LIST.
        """
        response = self._call_with_retry(prompt)
        try:
            cleaned_json = self.clean_json_response(response)
            return json.loads(cleaned_json)
        except Exception as e:
            print(f"Error parsing daily summary JSON: {e}")
            return [{"type": "intro", "text": f"नमस्कार, {channel_name}मा हजुरलाइ स्वागत छ | आजको मुख्य समाचार यसप्रकार छन्", "gender": "female"}]

    def clean_script(self, text: str) -> str:
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'^(Anchor|Narrator|Voiceover|Anchorperson|Speaker):\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'#\w+', '', text)
        return text.strip()

    def clean_json_response(self, text: str) -> str:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match: return match.group(1).strip()
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match: return match.group(1).strip()
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1: return text[start:end+1].strip()
        return text.strip()

    def generate_image_keywords(self, text: str, extra_context: str = "Nepal") -> List[str]:
        """
        Generates a list of keywords for different segments of the text to provide visual variety.
        """
        # Split by sentence or paragraph to get segments, but keep them simple for visual search
        segments = [s.strip() for s in re.split(r'[।.\n]', text) if len(s.strip()) > 20]
        if not segments: segments = [text]
        
        all_keywords = []
        for seg in segments[:8]: 
            prompt = f"""
            Extract a single, simple, concrete 1-2 word noun from this text that represents a visual subject.
            Text: "{seg}"
            Rules: NO humans, NO faces, NO text, NO interviews, NO talking heads. NO adjectives unless necessary. NO broad concepts. Simple subjects (e.g., 'nebula', 'satellite', 'earth', 'mountains').
            Output ONLY the subject.
            """
            try:
                keywords = self._call_with_retry(prompt)
                clean_kw = keywords.replace('"', '').strip().split('\n')[0].strip()
                if clean_kw: all_keywords.append(clean_kw)
            except:
                continue
        
        if not all_keywords:
            return [f"{extra_context} cinematic"]
        return all_keywords
