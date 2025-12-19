import asyncio
import os
from dotenv import load_dotenv
from processors.rewrite_breaking import ScriptRewriter
from media.tts_english import TTSEngine # Still named tts_english.py for now

load_dotenv()

async def test_nepali_pipeline():
    print("--- Testing Nepali Script Generation ---")
    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    headline = "Nepal celebrates Constitution Day with nationwide events"
    content = "Constitution Day is being observed across Nepal with various programs. The government has organized a special ceremony at Tundikhel in Kathmandu."
    
    script = rewriter.rewrite_for_shorts(headline, content)
    print(f"Generated Script:\n{script}\n")
    
    if not any(ord(c) > 127 for c in script):
        print("WARNING: Script does not appear to contain Devanagari characters.")
    else:
        print("SUCCESS: Script contains Devanagari characters.")

    print("\n--- Testing Nepali TTS Generation ---")
    audio_path = "test_nepali_audio.mp3"
    _, word_offsets = await TTSEngine.generate_audio(script, audio_path)
    
    if os.path.exists(audio_path):
        print(f"SUCCESS: Audio generated at {audio_path}")
        print(f"Number of word offsets: {len(word_offsets)}")
    else:
        print("FAILED: Audio generation failed.")

if __name__ == "__main__":
    asyncio.run(test_nepali_pipeline())
