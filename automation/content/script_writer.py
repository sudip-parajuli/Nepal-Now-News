from google import genai
from google.genai import errors
import os
import time
import random
import json
import re
from typing import List, Dict

class ScriptWriter:
    def __init__(self, api_key: str = None):
        # Gather all Gemini keys from env
        self.api_keys = [
            os.getenv("GEMINI_API_KEY"),
            os.getenv("GEMINI_API_KEY2"),
            os.getenv("GEMINI_API_KEY3")
        ]
        # Filter out empty/None keys
        self.api_keys = [k for k in self.api_keys if k]
        
        # If no key found in env, but one was passed to init, use it
        if not self.api_keys and api_key:
            self.api_keys = [api_key]
            
        self.clients = [genai.Client(api_key=k) for k in self.api_keys]
        self.client = self.clients[0] if self.clients else None
        self.model_id = 'gemini-2.0-flash'
        self.groq_api_keys = [
            os.getenv("GROQ_API_KEY"),
            os.getenv("GROQ_API_KEY2"),
            os.getenv("GROQ_API_KEY3")
        ]
        self.groq_api_keys = [k for k in self.groq_api_keys if k]
        self.groq_clients = []
        if self.groq_api_keys:
            try:
                from groq import Groq
                self.groq_clients = [Groq(api_key=k) for k in self.groq_api_keys]
            except ImportError:
                pass
        self.groq_client = self.groq_clients[0] if self.groq_clients else None


    def _call_with_retry(self, prompt: str, max_retries: int = 5) -> str:
        """Calls Gemini rotating through keys, falling back to Groq only if all fail or hit quota."""
        if not self.clients:
            print("WARNING: No Gemini clients available. Trying Groq immediately...")
        
        # Try each Gemini client sequentially
        for client_idx, client in enumerate(self.clients):
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=self.model_id,
                        contents=prompt
                    )
                    return response.text.strip()
                except Exception as e:
                    err_msg = str(e).lower()
                    is_quota_error = "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg
                    
                    if is_quota_error:
                        print(f"Gemini Key {client_idx+1} Quota Exceeded/429. Trying next key...")
                        break  # Break out of attempts loop for this key, move to next key
                    
                    # For non-quota errors, retry with exponential backoff on the current key
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random.uniform(0, 1)
                        print(f"LLM Error on Key {client_idx+1}: {e}. Retrying in {wait_time:.2f} seconds... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print(f"LLM Key {client_idx+1} failed after {max_retries} attempts. Trying next key...")
                        break
        
        # If all Gemini keys fail or are exhausted, try Groq fallback
        if self.groq_clients:
            print("All Gemini keys exhausted. Trying Groq fallback...")
            for client_idx, groq_client in enumerate(self.groq_clients):
                for attempt in range(max_retries):
                    try:
                        chat_completion = groq_client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        )
                        result = chat_completion.choices[0].message.content.strip()
                        if result:
                            return result
                    except Exception as groq_err:
                        err_msg = str(groq_err).lower()
                        is_quota_error = "quota" in err_msg or "429" in err_msg or "exhausted" in err_msg
                        
                        if is_quota_error:
                            print(f"Groq Key {client_idx+1} Quota Exceeded/429. Trying next key...")
                            break
                        
                        print(f"Groq fallback Key {client_idx+1} attempt {attempt+1} failed: {groq_err}")
                        if attempt < max_retries - 1:
                            time.sleep((2 ** attempt) + 1)
                            
        return "Error: Maximum retries reached for all LLM keys and fallbacks."

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
        if "Maximum retries" in script or not script.strip():
            return f"Did you know that the science of *{topic}* contains mysteries that continue to challenge researchers? Across the cosmos, these phenomena push the boundaries of physics, reminding us of how much remains to be discovered."
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
        if "Maximum retries" in script or not script.strip():
            return f"The universe is full of mysteries, and *{topic}* is one of the most intriguing. For centuries, researchers have sought to understand its complex mechanisms. From molecular scales to cosmic proportions, this phenomenon continues to redefine our understanding of nature. As we look closer, we uncover secrets that challenge our conventional theories. In the end, it reminds us that our search for knowledge is an endless journey."
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
        1. Terms must be ready-to-search queries (e.g. "Hubble telescope nebula deep space", "close up macro leaf cells").
        2. STRICTLY NO HUMANS, NO FACES, NO PEOPLE, NO CHARACTERS, NO TEXT, NO CARTOONS, NO ANIMATION, NO ANIMALS, NO MOVIES. ONLY PURE SCIENCE.
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
        Enforces 6 visual types, max 3 ai_videos, and parses thumbnail_data.
        """
        # Initialize default fallback thumbnail data
        self.last_thumbnail_data = {
            "hook_phrase": topic[:25].upper(),
            "supporting_fact": "A scientific discovery.",
            "thumbnail_bg_query": f"cinematic 4k photo of {topic}, scientific, deep space",
            "thumbnail_subject_query": ""
        }

        # First try: Rich, detailed prompt
        prompt = f"""
You are a visual director for a science YouTube channel called "Daily Deep Space".
You will be given a narration script about "{topic}".
Break the script into 15-20 visual SCENES. For each scene assign one of the 6 visual types:

1. `typewriter_text` - Use for opening hooks, key revelations, named discoveries.
   Fields: "typewriter_words": list of dicts: [{{"word": "word1", "weight": "bold"}}, {{"word": "word2", "weight": "md"}}]. Give important emphasis words a weight of "bold", and regular words a weight of "md".
2. `kinetic_stat`    - Use for a single overwhelming number.
   Fields: "stat_data": object with "value" (number/string), "unit" (string), "label" (string). Do not use unless you actually have statistical data for this scene.
3. `image`           - Use for real places, scientists, historical events.
   Fields: "named_entity": string (optional, to display as lower third).
4. `ai_video`        - Use for abstract phenomena (space, physics, microscopic).
   Fields: "ai_video_prompt": text-to-video prompt. Max 3 scenes of this type!
5. `hook_question`   - Use for chapter openings, rhetorical questions.
   Fields: "question_text": string, "emphasis_phrase": string (key words/phrase in ALL CAPS, never null).
6. `data_bars`       - Use for comparing 3+ values.
   Fields: "bar_data": list of 3-4 objects, each with "label" (string) and "value" (number).

STRICT RULES FOR FIELDS:
1. `image_cue` MUST be a specific, descriptive, non-empty search query (never null, never the word 'None' or empty string).
2. For `hook_question` scenes, you MUST provide `question_text` and a non-empty `emphasis_phrase` string (key words/phrase in ALL CAPS).
3. For `typewriter_text` scenes, `typewriter_words` MUST be a list of dictionaries where each dictionary contains {{"word": "example", "weight": "bold"}} or {{"word": "example", "weight": "md"}}. Give important emphasis words a weight of "bold", and regular words a weight of "md".
4. For `kinetic_stat` scenes, you MUST provide non-null `stat_data` containing "value", "unit", and "label". If a scene does not have statistical data, do not use `kinetic_stat`.

Additionally, generate metadata for the YouTube THUMBNAIL:
- `hook_phrase`: Max 4 words, ALL CAPS, creates curiosity or shock. Never generic titles like "THE SCIENCE OF".
- `supporting_fact`: Short supporting fact/stat in 5-8 words.
- `thumbnail_bg_query`: DDG search term for a space/science background.
- `thumbnail_subject_query`: DDG search term for a main subject image to composite.

Return ONLY a valid JSON object of this structure:
{{
  "scenes": [
    {{
      "narration": "Verbatim narration from script",
      "visual_type": "typewriter_text",
      "image_cue": "search term for backup image",
      "typewriter_words": [{{"word": "word1", "weight": "bold"}}, {{"word": "word2", "weight": "md"}}],
      "stat_data": null,
      "named_entity": null,
      "ai_video_prompt": "",
      "question_text": null,
      "emphasis_phrase": null,
      "bar_data": null
    }}
  ],
  "thumbnail_data": {{
    "hook_phrase": "ALL CAPS HOOK",
    "supporting_fact": "supporting fact",
    "thumbnail_bg_query": "nebula space",
    "thumbnail_subject_query": "bismuth crystal"
  }}
}}

Script:
\"\"\"{script[:4000]}\"\"\"
"""
        raw = self._call_with_retry(prompt)
        scenes = []
        parsed_ok = False

        try:
            cleaned = self.clean_json_response(raw)
            data = json.loads(cleaned)
            if isinstance(data, dict) and "scenes" in data:
                scenes = data["scenes"]
                if len(scenes) >= 5:
                    self.last_thumbnail_data = data.get("thumbnail_data", self.last_thumbnail_data)
                    parsed_ok = True
        except Exception as e:
            print(f"[ScriptWriter] Primary visual scenes JSON parse error: {e}")

        # If primary prompt fails or returns less than 5 scenes, try simplified prompt retry
        if not parsed_ok:
            print("[ScriptWriter] Retrying visual scenes generation with simplified prompt...")
            simple_prompt = f"""
Analyze this science script about "{topic}" and generate a JSON list of 15-20 visual scenes.
For each scene, output ONLY:
- "narration": verbatim sentence(s)
- "visual_type": one of: "typewriter_text", "kinetic_stat", "image", "ai_video", "hook_question", "data_bars"
- "image_cue": 4-8 word search term

Also include:
- "thumbnail_data": {{
    "hook_phrase": "MAX 4 WORDS ALL CAPS",
    "supporting_fact": "Short fact",
    "thumbnail_bg_query": "bg search term",
    "thumbnail_subject_query": "subject search term"
  }}

Return ONLY a valid JSON object:
{{
  "scenes": [
    {{ "narration": "...", "visual_type": "...", "image_cue": "..." }}
  ],
  "thumbnail_data": {{ ... }}
}}

Script:
\"\"\"{script[:3000]}\"\"\"
"""
            raw_retry = self._call_with_retry(simple_prompt)
            try:
                cleaned_retry = self.clean_json_response(raw_retry)
                data_retry = json.loads(cleaned_retry)
                if isinstance(data_retry, dict) and "scenes" in data_retry:
                    scenes = data_retry["scenes"]
                    self.last_thumbnail_data = data_retry.get("thumbnail_data", self.last_thumbnail_data)
            except Exception as retry_err:
                print(f"[ScriptWriter] Secondary retry parsing failed: {retry_err}")

        # If still no scenes, create bare basic scenes to let the pipeline run
        if not scenes:
            print("[ScriptWriter] WARNING: Visual scenes completely empty, creating fallback default scenes...")
            sentences = [s.strip() for s in script.split('.') if s.strip()]
            for s in sentences[:8]:
                scenes.append({
                    "narration": s + ".",
                    "visual_type": "image",
                    "image_cue": f"{topic} space background",
                    "typewriter_words": None,
                    "stat_data": None,
                    "named_entity": None,
                    "ai_video_prompt": "",
                    "question_text": None,
                    "emphasis_phrase": None,
                    "bar_data": None
                })

        # Sanitize and upgrade scenes to meet fields and budget rules
        ai_count = 0
        final_scenes = []
        for s in scenes:
            if not isinstance(s, dict):
                continue
            vtype = s.get("visual_type", "image")
            if vtype not in ["typewriter_text", "kinetic_stat", "image", "ai_video", "hook_question", "data_bars"]:
                vtype = "image"
            
            # Enforce hard cap of 3 ai_videos
            if vtype == "ai_video":
                if ai_count >= 3:
                    print("[ScriptWriter] Enforcing ai_video cap — downgrading scene to image")
                    vtype = "image"
                else:
                    ai_count += 1
            
            s["visual_type"] = vtype
            
            # Ensure all required fields exist to prevent KeyErrors later
            s.setdefault("narration", "")
            s.setdefault("image_cue", f"{topic} science background")
            s.setdefault("typewriter_words", None)
            s.setdefault("stat_data", None)
            s.setdefault("named_entity", None)
            s.setdefault("ai_video_prompt", "")
            s.setdefault("question_text", None)
            s.setdefault("emphasis_phrase", None)
            s.setdefault("bar_data", None)

            final_scenes.append(s)

        print(f"[ScriptWriter] Final Visual Scenes Manifest: {len(final_scenes)} scenes ({ai_count} ai_video).")
        return final_scenes

    def generate_shorts_visual_scenes(self, topic: str, script: str) -> List[Dict]:
        """
        Generates a scene-by-scene structured JSON list for the shorts visual pipeline.
        Enforces 6 visual types, max 2 ai_videos, and parses thumbnail_data.
        """
        # Initialize default fallback thumbnail data
        self.last_thumbnail_data = {
            "hook_phrase": topic[:25].upper(),
            "supporting_fact": "A scientific discovery.",
            "thumbnail_bg_query": f"cinematic 4k photo of {topic}, scientific, deep space",
            "thumbnail_subject_query": ""
        }

        # First try: Rich, detailed prompt
        prompt = f"""
You are a visual director for a science YouTube channel called "Daily Deep Space".
You will be given a narration script about "{topic}".
Break the script into EXACTLY 5 visual SCENES total for a YouTube Short.
For each scene assign one of these 5 visual types following this STRICT mix:
- 1 `hook_question` (must be the opening scene 1)
- 1-2 `typewriter_text`
- 1-2 `image` or `ai_video` (max 1 `ai_video` total)
- 0-1 `kinetic_stat`
DO NOT use data_bars.

1. `hook_question`   - Use for chapter openings, rhetorical questions.
   Fields: "question_text": string, "emphasis_phrase": string (key words/phrase in ALL CAPS, never null).
2. `typewriter_text` - Use for opening hooks, key revelations, named discoveries.
   Fields: "typewriter_words": list of dicts: [{{"word": "word1", "weight": "bold"}}, {{"word": "word2", "weight": "md"}}]. Give important emphasis words a weight of "bold", and regular words a weight of "md".
3. `kinetic_stat`    - Use for a single overwhelming number.
   Fields: "stat_data": object with "value" (number/string), "unit" (string), "label" (string). Do not use unless you actually have statistical data for this scene.
4. `image`           - Use for real places, scientists, historical events.
   Fields: "named_entity": string (optional, to display as lower third).
5. `ai_video`        - Use for abstract phenomena (space, physics, microscopic).
   Fields: "ai_video_prompt": text-to-video prompt. Max 1 scenes of this type!

STRICT RULES FOR FIELDS:
1. `image_cue` MUST be a specific, descriptive, non-empty search query (never null, never the word 'None' or empty string).
2. For `hook_question` scenes, you MUST provide `question_text` and a non-empty `emphasis_phrase` string (key words/phrase in ALL CAPS).
3. For `typewriter_text` scenes, `typewriter_words` MUST be a list of dictionaries where each dictionary contains {{"word": "example", "weight": "bold"}} or {{"word": "example", "weight": "md"}}. Give important emphasis words a weight of "bold", and regular words a weight of "md".
4. For `kinetic_stat` scenes, you MUST provide non-null `stat_data` containing "value", "unit", and "label". If a scene does not have statistical data, do not use `kinetic_stat`.

Additionally, generate metadata for the YouTube THUMBNAIL (portrait format):
- `hook_phrase`: Max 4 words, ALL CAPS, creates curiosity or shock. Never generic titles like "THE SCIENCE OF".
- `supporting_fact`: Short supporting fact/stat in 5-8 words.
- `thumbnail_bg_query`: DDG search term for a space/science background.
- `thumbnail_subject_query`: DDG search term for a main subject image to composite.

Return ONLY a valid JSON object of this structure:
{{
  "scenes": [
    {{
      "narration": "Verbatim narration from script",
      "visual_type": "typewriter_text",
      "image_cue": "search term for backup image",
      "typewriter_words": [{{"word": "word1", "weight": "bold"}}, {{"word": "word2", "weight": "md"}}],
      "stat_data": null,
      "named_entity": null,
      "ai_video_prompt": "",
      "question_text": null,
      "emphasis_phrase": null
    }}
  ],
  "thumbnail_data": {{
    "hook_phrase": "ALL CAPS HOOK",
    "supporting_fact": "supporting fact",
    "thumbnail_bg_query": "nebula space",
    "thumbnail_subject_query": "bismuth crystal"
  }}
}}

Script:
\"\"\"{script[:4000]}\"\"\"
"""
        raw = self._call_with_retry(prompt)
        scenes = []
        parsed_ok = False

        try:
            cleaned = self.clean_json_response(raw)
            data = json.loads(cleaned)
            if isinstance(data, dict) and "scenes" in data:
                scenes = data["scenes"]
                if len(scenes) >= 3:
                    self.last_thumbnail_data = data.get("thumbnail_data", self.last_thumbnail_data)
                    parsed_ok = True
        except Exception as e:
            print(f"[ScriptWriter] Primary shorts visual scenes JSON parse error: {e}")

        # If primary prompt fails, try simplified prompt retry
        if not parsed_ok:
            print("[ScriptWriter] Retrying shorts visual scenes generation with simplified prompt...")
            simple_prompt = f"""
Analyze this science script about "{topic}" and generate a JSON list of EXACTLY 5 visual scenes.
For each scene, output ONLY:
- "narration": verbatim sentence(s)
- "visual_type": one of: "typewriter_text", "kinetic_stat", "image", "ai_video", "hook_question"
- "image_cue": 4-8 word search term

Also include:
- "thumbnail_data": {{
    "hook_phrase": "MAX 4 WORDS ALL CAPS",
    "supporting_fact": "Short fact",
    "thumbnail_bg_query": "bg search term",
    "thumbnail_subject_query": "subject search term"
  }}

Return ONLY a valid JSON object:
{{
  "scenes": [
    {{ "narration": "...", "visual_type": "...", "image_cue": "..." }}
  ],
  "thumbnail_data": {{ ... }}
}}

Script:
\"\"\"{script[:3000]}\"\"\"
"""
            raw_retry = self._call_with_retry(simple_prompt)
            try:
                cleaned_retry = self.clean_json_response(raw_retry)
                data_retry = json.loads(cleaned_retry)
                if isinstance(data_retry, dict) and "scenes" in data_retry:
                    scenes = data_retry["scenes"]
                    self.last_thumbnail_data = data_retry.get("thumbnail_data", self.last_thumbnail_data)
            except Exception as retry_err:
                print(f"[ScriptWriter] Secondary shorts retry parsing failed: {retry_err}")

        # If still no scenes, create bare basic scenes to let the pipeline run
        if not scenes:
            print("[ScriptWriter] WARNING: Shorts visual scenes completely empty, creating fallback default scenes...")
            sentences = [s.strip() for s in script.split('.') if s.strip()]
            for s in sentences[:8]:
                scenes.append({
                    "narration": s + ".",
                    "visual_type": "image",
                    "image_cue": f"{topic} space background",
                    "typewriter_words": None,
                    "stat_data": None,
                    "named_entity": None,
                    "ai_video_prompt": "",
                    "question_text": None,
                    "emphasis_phrase": None
                })

        # Sanitize and upgrade scenes to meet fields and budget rules
        ai_count = 0
        final_scenes = []
        for s in scenes:
            if not isinstance(s, dict):
                continue
            vtype = s.get("visual_type", "image")
            if vtype not in ["typewriter_text", "kinetic_stat", "image", "ai_video", "hook_question"]:
                vtype = "image"
            
            if vtype == "ai_video":
                if ai_count >= 1:
                    print("[ScriptWriter] Enforcing ai_video cap — downgrading scene to image")
                    vtype = "image"
                else:
                    ai_count += 1
            
            s["visual_type"] = vtype
            
            # Ensure all required fields exist to prevent KeyErrors later
            s.setdefault("narration", "")
            s.setdefault("image_cue", f"{topic} science background")
            s.setdefault("typewriter_words", None)
            s.setdefault("stat_data", None)
            s.setdefault("named_entity", None)
            s.setdefault("ai_video_prompt", "")
            s.setdefault("question_text", None)
            s.setdefault("emphasis_phrase", None)

            final_scenes.append(s)
            
            # Enforce max 5 scenes
            if len(final_scenes) >= 5:
                break

        print(f"[ScriptWriter] Final Shorts Visual Scenes Manifest: {len(final_scenes)} scenes ({ai_count} ai_video).")
        return final_scenes

    def generate_thumbnail_info(self, topic: str, script: str) -> Dict[str, str]:
        """Generates catchy thumbnail metadata, leveraging cached last_thumbnail_data from generate_visual_scenes."""
        if hasattr(self, 'last_thumbnail_data') and self.last_thumbnail_data:
            thumb = self.last_thumbnail_data
            # Enforce hook phrase formatting: max 4 words, ALL CAPS
            hook = str(thumb.get("hook_phrase", "")).strip().upper()
            words = hook.split()
            if len(words) > 4:
                hook = " ".join(words[:4])
            
            return {
                "text": hook or topic[:25].upper(),
                "image_prompt": thumb.get("thumbnail_bg_query", f"cinematic 4k photo of {topic}, scientific, deep space"),
                "hook_phrase": hook or topic[:25].upper(),
                "supporting_fact": thumb.get("supporting_fact", "A scientific revelation."),
                "thumbnail_bg_query": thumb.get("thumbnail_bg_query", f"cinematic 4k photo of {topic}, scientific, deep space"),
                "thumbnail_subject_query": thumb.get("thumbnail_subject_query", "")
            }
        
        # Generic fallback
        return {
            "text": topic[:25].upper(),
            "image_prompt": f"cinematic 4k photo of {topic}, scientific, deep space",
            "hook_phrase": topic[:25].upper(),
            "supporting_fact": "A scientific revelation.",
            "thumbnail_bg_query": f"cinematic 4k photo of {topic}, scientific, deep space",
            "thumbnail_subject_query": ""
        }
