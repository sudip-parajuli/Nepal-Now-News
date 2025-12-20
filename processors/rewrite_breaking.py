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

    def summarize_for_daily(self, news_items: list) -> str:
        news_text = "\n\n".join([f"Headline: {item['headline']}\nContent: {item['content']}" for item in news_items])
        prompt = f"""
        Summarize today's major news into a 6–8 minute YouTube video script in Nepali.
        
        News items:
        {news_text}

        Language: Nepali (Devanagari)
        Tone: Professional news anchor, formal.
       - Use standard Nepali news reporting grammar and formal vocabulary.
        - Ensure perfect grammatical structure and natural transitions.
        - Group related stories logically.
        - RETURN ONLY THE NEPALI SPEECH TEXT.
        - DO NOT include any labels like "Segment" or "Visual".
        - Translate English news terms into proper Nepali reporting terms.
        """
        script = self._call_with_retry(prompt)
        return self.clean_script(script)

    def generate_image_keywords(self, sentence: str) -> str:
        """
        Generates 3-5 descriptive keywords for an image search based on the sentence.
        Aims for 'news-worthy' photographic subjects.
        """
        prompt = f"""
        Extract 3-5 highly descriptive keywords for a news photographic image search from this sentence:
        "{sentence}"
        
        Rules:
        - Focus on real-world objects, people, or locations.
        - AVOID generic words like "system", "process", "decision", "random".
        - AVOID abstract concepts or diagrams.
        - Output ONLY the keywords separated by spaces.
        - Example: "US government discontinues lottery" -> "US Capitol Building Immigration"
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
