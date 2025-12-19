import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class ScriptRewriter:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def rewrite_for_shorts(self, headline: str, content: str) -> str:
        prompt = f"""
        Rewrite this international breaking news into a 25–40 second YouTube Shorts script.
        Headline: {headline}
        Content: {content}

        Language: English
        Tone: Urgent, neutral, factual
        No opinions or assumptions
        Simple global English
        End with: 'More updates will follow.'
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def summarize_for_daily(self, news_items: list) -> str:
        news_text = "\n\n".join([f"Headline: {item['headline']}\nContent: {item['content']}" for item in news_items])
        prompt = f"""
        Summarize today’s major international news into a 6–8 minute YouTube video script.
        
        News items:
        {news_text}

        Language: English
        Tone: Professional news anchor
        Group related stories
        Use clear transitions between topics
        Avoid repetition or bias
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

if __name__ == "__main__":
    API_KEY = os.getenv("GEMINI_API_KEY")
    if API_KEY:
        rewriter = ScriptRewriter(API_KEY)
        # Test Shorts
        # script = rewriter.rewrite_for_shorts("Earthquake in Japan", "A magnitude 7.5 earthquake...")
        # print(script)
    else:
        print("GEMINI_API_KEY not found.")
