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

    def _dummy_placeholder(self):
        pass

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
        - **IMPORTANT**: Wrap key entities (Names, Numbers, Shocking Adjectives) in asterisks for highlighting. Example: "The *Sun* is *400 times* larger than the *Moon*."
        - RETURN ONLY THE ENGLISH SPEECH TEXT.
        - DO NOT include music cues or labels like [Narrator].
        """
        script = self._call_with_retry(prompt)
        return self.clean_script(script)
    def expand_science_script(self, topic: str) -> str:
        """
        Generates a master-class 900-word documentary script using the user's high-quality prompts.
        """
        # We alternate between the two styles provided by the user for variety
        style = random.choice(["paradox", "discovery"])
        
        if style == "paradox":
            hook_instr = "Open with an unexplained observation or paradox before naming the topic. Make the viewer feel that something is wrong with how they understand reality."
        else:
            hook_instr = "Open by narrating the specific moment a scientist or explorer first encountered this phenomenon. Use their name, the year, and sensory detail."

        prompt = f"""
        You are writing a master-class YouTube narration script for a science education channel.
        Topic: "{topic}"

        HOOK STYLE: {hook_instr}

        TONE & VOICE:
        Voice of awe and wonder — treat science as magic that actually works. Sentences are punchy and declarative. 
        Never use filler phrases like "in the realm of", "profound implications", "awe-inspiring complexity", or "testament to human curiosity". 
        Be specific at all times — name scientists, cite dates, use precise numbers.

        STRUCTURE & LENGTH:
        Target approximately 900 words (~6 minutes). 
        Structure: hook → background context → core science mechanism → recent discovery or application → broader implications → memorable closing line.
        End on a single surprising or poetic image that reframes what the viewer just learned.

        SCIENCE ACCURACY:
        Every mechanism must be explained causally — not just "X causes Y" but "X causes Y because of Z". 
        Avoid vague words like "unique", "fascinating", "complex" unless immediately followed by a specific example.

        VISUAL CUES:
        This script is for an AI-automated channel. After every 2-3 sentences, add a short bracketed image cue in plain language, 
        e.g. [microscope image of bismuth crystal surface] or [NASA photo of pulsar nebula].

        OUTPUT FORMAT:
        Write the full script ONLY. No meta-commentary. Begin with the first word of the narration.
        **IMPORTANT**: Wrap key technical terms, numbers, or specific names in asterisks for visual highlighting.
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

    def generate_image_keywords(self, text: str, extra_context: str = "Science", is_long_form: bool = False) -> List[str]:
        """
        Generates a list of specific visual search terms for the script.
        Uses the LLM to analyze the entire text and produce timed visual cues.
        """
        count = 35 if is_long_form else 12
        prompt = f"""
        Analyze this science script and generate {count} SPECIFIC, VIVID, and CONCRETE visual search terms for Pexels/Storyblocks/NASA.
        
        Script: "{text[:3000]}..." 
        Context: {extra_context}

        Requirements:
        1. Terms must be ready-to-search queries (e.g. "glowing bioluminescent jellyfish 4k", "Hubble telescope nebula deep space", "time lapse plant growth").
        2. STRICTLY NO HUMANS, NO FACES, NO PEOPLE, NO CHARACTERS, NO TEXT.
        3. For each segment of the script (Intro, Body sections, Conclusion), provide diverse queries.
        4. Prioritize cinematic, 4k, macro, or animation styles.
        5. Return ONLY the search terms, one per line. No numbers or bullet points.
        """
        
        try:
            response = self._call_with_retry(prompt)
            keywords = []
            for line in response.split('\n'):
                line = line.strip()
                if not line or line.lower().startswith(("here", "sure", "ok", "based")): continue
                # Strip leading numbers like "1. ", "1) ", " - ", " * "
                line = re.sub(r'^(\d+[\.\)]\s*|[-\*\u2022]\s*)', '', line)
                line = line.replace('"', '').strip()
                if line: keywords.append(line)
            
            # Fallback if LLM fails
            if not keywords:
                keywords = [f"{extra_context} cinematic 4k"] * 10
                
            return keywords[:count + 5] 
        except Exception as e:
            print(f"Keyword Gen Error: {e}")
            return [f"{extra_context} science background"] * 10

    def generate_thumbnail_info(self, topic: str, script: str) -> Dict[str, str]:
        """Generates a catchy thumbnail text and a specific background image prompt."""
        prompt = f"""
        Based on this science script about "{topic}", generate two things for a YouTube thumbnail:
        1. A catchy, curiosity-driven short phrase (max 4-5 words). It should NOT just repeat the title. It should create intrigue (e.g. "The Hidden Truth", "It Shouldn't Exist", "Physics Broken?").
        2. A vivid image generation prompt for the background (no people, high contrast, cinematic, scientific).

        Script: "{script[:1500]}..."

        Return ONLY a JSON object:
        {{
          "text": " Catchy Phrase Here",
          "image_prompt": "Image prompt here"
        }}
        """
        response = self._call_with_retry(prompt)
        try:
            cleaned = self.clean_json_response(response)
            return json.loads(cleaned)
        except:
            return {
                "text": topic[:25],
                "image_prompt": f"cinematic 4k photo of {topic}, scientific, deep space"
            }
