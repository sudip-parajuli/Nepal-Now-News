from google import genai
from google.genai import errors
import os
import time
import random
from dotenv import load_dotenv

load_dotenv()

class ScriptRewriter:
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
                # Handle Quota / Resource Exhausted
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
        - Use standard Nepali news reporting grammar (e.g., prefer "फैलिएको छ" over "फैलियो छ").
        - Ensure natural flow and correct tense usage.
        - RETURN ONLY THE NEPALI SPEECH TEXT. 
        - DO NOT include narrator instructions or speaker labels.
        - Translate English news terms into proper Nepali reporting terms.
        End with: 'थप अपडेटका लागि हामीसँगै रहनुहोला।'
        """
        script = self._call_with_retry(prompt)
        return self.clean_script(script)

    def clean_script(self, text: str) -> str:
        """Removes common narrator patterns like [Music] or Anchor: from text."""
        import re
        # Remove patterns like [Music plays], [Serious music], (Upbeat tone)
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)
        # Remove speaker labels like Anchor:, Narrator:, Voiceover:
        text = re.sub(r'^(Anchor|Narrator|Voiceover|Anchorperson):\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        return text.strip()

    def summarize_for_daily(self, news_items: list) -> list:
        news_text = "\n\n".join([f"Headline: {item['headline']}\nContent: {item['content']}" for item in news_items])
        prompt = f"""
        Summarize today's major news into a structured YouTube video script in Nepali.
        
        News items:
        {news_text}

        Language: Nepali (Devanagari)
        Goal: Create a professional news report.
        
        Output Format: JSON list of objects.
        Required structure:
        [
          {{"type": "intro", "text": "नमस्कार, नेपाल नाउमा हजुरलाइ स्वागत छ | आजको मुख्य समाचार यसप्रकार छन्", "gender": "female"}},
          {{"type": "news", "headline": "HEADLINE_HERE", "text": "NEWS_CONTENT_HERE", "gender": "male"}},
          {{"type": "news", "headline": "HEADLINE_HERE", "text": "NEWS_CONTENT_HERE", "gender": "female"}},
          ...
          {{"type": "outro", "text": "थप अपडेटका लागि हामीसँगै रहनुहोला। धन्यवाद।", "gender": "male"}}
        ]

        Rules:
        - Alternate gender (male/female) for each news item.
        - The intro should ALWAYS be "नमस्कार, नेपाल नाउमा हजुरलाइ स्वागत छ | आजको मुख्य समाचार यसप्रकार छन्".
        - The outro should be a closing statement.
        - Headlines should be short and catchy.
        - Text should be professional news reporting style.
        - RETURN ONLY THE JSON LIST.
        """
        response = self._call_with_retry(prompt)
        try:
            import json
            cleaned_json = self.clean_json_response(response)
            segments = json.loads(cleaned_json)
            # Ensure intro/outro text is exactly as requested
            if segments and isinstance(segments, list) and segments[0]['type'] == 'intro':
                segments[0]['text'] = "नमस्कार, नेपाल नाउमा हजुरलाइ स्वागत छ | आजको मुख्य समाचार यसप्रकार छन्"
            return segments
        except Exception as e:
            print(f"Error parsing daily summary JSON: {e}")
            # Fallback to a single segment if JSON fails
            return [{"type": "intro", "text": "नमस्कार, नेपाल नाउमा हजुरलाइ स्वागत छ | आजको मुख्य समाचार यसप्रकार छन्", "gender": "female"}]

    def clean_json_response(self, text: str) -> str:
        """Removes markdown code blocks and extra text around JSON."""
        import re
        # Try to find content between ```json and ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Try to find content between ``` and ```
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Find first [ and last ]
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return text[start:end+1].strip()
        return text.strip()

    def generate_image_keywords(self, sentence: str) -> str:
        """
        Generates specific, context-rich keywords for an image search based on the sentence.
        Aims for highly accurate, representative news photography.
        """
        prompt = f"""
        Generate a highly specific English image search query (5-8 words) for this news:
        "{sentence}"
        
        Rules:
        - Must capture the core event, people, and specific context.
        - Always include 'Nepal' or 'Nepali' if the news is about Nepal or Nepali people.
        - Be extremely specific to avoid generic or confusing results (e.g., if a tribute is given, search for the specific community and event).
        - AVOID generic concepts or single words like 'accident' or 'tribute' alone.
        - Output ONLY the search query keywords separated by spaces.
        - Example: "Buddhist community tribute Nepali student car accident" -> "Nepal Buddhist community tribute student car accident funeral"
        """
        
        try:
            keywords = self._call_with_retry(prompt)
            # Clean up formatting
            return " ".join(keywords.replace('"', '').replace(',', ' ').split())
        except:
            # Fallback to simple extraction
            words = [w for w in sentence.split() if len(w) > 4]
            return " ".join(words[:4])

if __name__ == "__main__":
    API_KEY = os.getenv("GEMINI_API_KEY")
    if API_KEY:
        rewriter = ScriptRewriter(API_KEY)
    else:
        print("GEMINI_API_KEY not found.")
