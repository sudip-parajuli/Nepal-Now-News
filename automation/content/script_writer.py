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
        Generates a master-class 900-word documentary script with expanded styles.
        """
        hooks = [
            ("paradox", "Open with an unexplained observation or paradox. Make the viewer feel that something is wrong with how they understand reality."),
            ("mystery", "Open with a genuine scientific mystery — something we only recently realized we don't understand."),
            ("scale", "Open by describing the mind-blowing scale or numbers involved (extreme sizes, temperatures, or speeds)."),
            ("counterintuitive", "Open with a counterintuitive fact that goes against common sense."),
            ("history", "Open by narrating the specific moment of discovery. Use names, dates, and sensory details of the lab or field site."),
            ("question", "Start with a direct, challenging question to the viewer that reframes a common object or idea.")
        ]
        tones = [
            ("awe", "Awe and wonder (Style: Kurzgesagt) — Treat science as magic that actually works."),
            ("conversational", "Conversational and curious (Style: Veritasium) — Build the logic from the ground up."),
            ("journalistic", "Journalistic deep-dive — Serious, factual, and investigative."),
            ("dramatic", "Dramatic narration — Build tension and release like a cinematic thriller.")
        ]
        
        hook_name, hook_instr = random.choice(hooks)
        tone_name, tone_instr = random.choice(tones)

        prompt = f"""
        You are writing a master-class YouTube narration script for a science education channel.
        Topic: "{topic}"

        HOOK STYLE: {hook_instr}
        TONE & VOICE: {tone_instr}

        STRICT NARRATIVE RULES:
        1. COGNITIVE DISSONANCE: Your hook must create immediate curiosity or a feeling that "this shouldn't be possible."
        2. NO VAGUE FILLERS: Never use phrases like "in the realm of", "profound implications", or "testament to curiosity". 
        3. SPECIFICITY: Use precise names, dates, and numbers. Cite specific scientists or missions.
        4. CAUSAL DEPTH: Every mechanism must be explained causally. Use "X happens because of Z" logic, not just "X causes Y."
        5. SENTENCE RHYTHM: Vary sentence length. Use short, punchy sentences (3-5 words) after long explanatory ones for impact.
        6. NO ROBOTIC TONE: Read this as if you are a brilliant friend explaining a secret of the universe.

        STRUCTURE & LENGTH:
        Target approximately 900 words (~6 minutes). 
        Structure: hook → background context → core science mechanism → recent discovery or application → broader implications → memorable closing line.
        End on a single surprising or poetic image that reframes the topic.

        VISUAL CUES:
        This is for an image-based workflow. Every 2 sentences, add a short [bracketed image cue] in plain language (e.g. [macro photo of bismuth crystals] or [NASA animation of a pulsar]).

        OUTPUT FORMAT:
        Write the full script ONLY. No meta-commentary. Begin with the first word of the narration.
        **IMPORTANT**: Wrap key technical terms, numbers, or names in single asterisks for visual highlighting.
        """
        
        script = self._call_with_retry(prompt)
        return self.clean_script(script)

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

    def generate_visual_scenes(self, topic: str, script: str) -> List[Dict]:
        """
        Generates a scene-by-scene structured JSON list for the visual pipeline.
        Each scene has: narration, visual_type, image_cue, ai_video_prompt,
        kinetic_stat, kinetic_overlay.

        Called separately from expand_science_script() — the plain-text TTS
        script is kept intact. This call only produces the visual routing data.

        Returns a List[Dict] with the schema below, or [] on failure.
        """
        prompt = f"""
You are a visual director for a science YouTube channel called "Daily Deep Space".
You will be given a narration script about "{topic}".
Break the script into 7-10 visual SCENES. For each scene assign:

1. "narration"      — verbatim sentence(s) from the script for this scene
2. "visual_type"    — one of: "ai_video", "image", "kinetic_text"
   Rules:
   - "ai_video"     — abstract phenomena: nebulae, crystal growth, chemical reactions,
                       atmospheric effects, space travel. NEVER for real people or places.
   - "image"        — real named places, historical events, specific objects/missions.
   - "kinetic_text" — when the narration contains a KEY STATISTIC, number, or short quote.
   HARD LIMIT: Maximum 3 scenes may be "ai_video". All others MUST be "image" or "kinetic_text".
3. "image_cue"      — a 4-8 word search term for an image (always fill this, even for ai_video)
4. "ai_video_prompt"— a cinematic text-to-video prompt for CogVideoX-2B
                       (only required for ai_video scenes; leave "" for others)
   Example: "extreme macro bismuth crystal surface, rainbow iridescent reflections,
              slow camera drift, cinematic 4K, photorealistic"
5. "kinetic_stat"   — object with "value" (number), "unit" (string), "label" (string)
                       ONLY for kinetic_text scenes that have a measurable quantity.
                       Set to null if the scene is a quote or text-only.
6. "kinetic_overlay"— true if the kinetic_text should appear as a lower-third overlay
                       on top of the image_cue image. false for full-screen stat slide.
                       Use true when a good base image exists for context.

Script:
\"\"\"{script[:4000]}\"\"\"

Return ONLY a valid JSON array. No markdown. No explanation. No trailing commas.
Example output:
[
  {{
    "narration": "The solar wind travels at over 1,100 kilometres per second.",
    "visual_type": "kinetic_text",
    "image_cue": "solar wind aurora borealis space",
    "ai_video_prompt": "",
    "kinetic_stat": {{"value": 1100, "unit": "km/s", "label": "Solar Wind Speed"}},
    "kinetic_overlay": true
  }},
  {{
    "narration": "Deep inside a neutron star, matter is compressed beyond imagination.",
    "visual_type": "ai_video",
    "image_cue": "neutron star pulsar deep space",
    "ai_video_prompt": "extreme close-up neutron star surface, glowing plasma jets, slow rotation, cinematic 4K, photorealistic, no text",
    "kinetic_stat": null,
    "kinetic_overlay": false
  }}
]
"""
        raw = self._call_with_retry(prompt)
        try:
            cleaned = self.clean_json_response(raw)
            scenes = json.loads(cleaned)
            if not isinstance(scenes, list):
                raise ValueError("Expected a JSON list")
            # Enforce hard cap: downgrade excess ai_video to image
            ai_count = 0
            for s in scenes:
                if s.get("visual_type") == "ai_video":
                    if ai_count >= 3:
                        print(f"[ScriptWriter] Downgrading scene to 'image' (ai_video cap reached)")
                        s["visual_type"] = "image"
                    else:
                        ai_count += 1
            print(f"[ScriptWriter] Generated {len(scenes)} visual scenes "
                  f"({ai_count} ai_video, "
                  f"{sum(1 for s in scenes if s.get('visual_type')=='image')} image, "
                  f"{sum(1 for s in scenes if s.get('visual_type')=='kinetic_text')} kinetic_text).")
            return scenes
        except Exception as e:
            print(f"[ScriptWriter] ERROR parsing visual scenes JSON: {e}")
            print(f"Raw response: {raw[:500]}")
            return []

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
