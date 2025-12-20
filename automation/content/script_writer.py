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
        Create an original educational YouTube Shorts script about "{topic}".
        
        Requirements:
        - Language: Nepali (Devanagari)
        - Duration: 35-45 seconds of speech.
        - Tone: Calm, educational, documentary-style.
        - Structure:
            1. Hook: Start with a mind-blowing fact or intriguing question.
            2. Content: Explain 2-3 key scientific aspects simply but accurately.
            3. Hook/Call to Action: End with a curiosity hook that makes the audience want to learn more.
        
        Rules:
        - Avoid clickbait or exaggeration.
        - Be scientifically accurate.
        - RETURN ONLY THE NEPALI SPEECH TEXT.
        - DO NOT include music cues or labels.
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

    def generate_image_keywords(self, sentence: str, extra_context: str = "Nepal") -> str:
        prompt = f"""
        Generate a highly specific English image search query (5-8 words) for this content:
        "{sentence}"
        
        Context: {extra_context}
        
        Rules:
        - Must capture the core event/subject.
        - Always include '{extra_context}' or relevant geography.
        - Output ONLY the keywords separated by spaces.
        """
        try:
            keywords = self._call_with_retry(prompt)
            return " ".join(keywords.replace('"', '').replace(',', ' ').split())
        except:
            words = [w for w in sentence.split() if len(w) > 4]
            return f"{extra_context} " + " ".join(words[:3])
