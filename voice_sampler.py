import asyncio
import os
from automation.media.tts import TTSEngine

async def generate_samples():
    tts_engine = TTSEngine(voice_map={"female": "ne-NP-HemkalaNeural"})
    
    text = """
    नमस्कार। आजको मुख्य समाचारमा स्वागत छ।
    नेपाल सरकारले नयाँ शिक्षा नीति सार्वजनिक गरेको छ।
    यसले शिक्षा क्षेत्रमा ठूलो परिवर्तन ल्याउने अपेक्षा गरिएको छ।
    """

    configs = [
        ("sample_1_bold_fast", "+10%", "-2Hz", "Bold & Fast"),
        ("sample_2_urgent", "+15%", "+0Hz", "Urgent/Breaking"),
        ("sample_3_deep_auth", "+5%", "-5Hz", "Deep Authority"),
        ("sample_4_balanced", "+8%", "-1Hz", "Balanced Fast")
    ]

    print("--- Generating Voice Samples ---")
    for name, rate, pitch, desc in configs:
        filename = f"automation/storage/{name}.mp3"
        print(f"Generating {desc} -> {filename} (Rate: {rate}, Pitch: {pitch})")
        await tts_engine.generate_audio(
            text, 
            filename, 
            voice="ne-NP-HemkalaNeural", 
            rate=rate, 
            pitch=pitch
        )
    print("--- Generation Complete ---")

if __name__ == "__main__":
    asyncio.run(generate_samples())
