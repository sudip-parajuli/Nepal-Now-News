import asyncio
import os
from automation.media.tts import TTSEngine

async def generate_samples_v3():
    tts_engine = TTSEngine()
    
    text = """
    नमस्कार। आजको मुख्य समाचारमा स्वागत छ।
    नेपाल सरकारले नयाँ शिक्षा नीति सार्वजनिक गरेको छ।
    यसले शिक्षा क्षेत्रमा ठूलो परिवर्तन ल्याउने अपेक्षा गरिएको छ।
    """

    # User liked: 
    # - Urgent Speed (+15%)
    # - High Pitch (+5Hz)
    # - Loud (-2Hz but loud volume)
    
    configs = [
        # Combo 1: Urgent Speed + High Pitch + High Volume
        ("v3_urgent_high", "ne-NP-HemkalaNeural", "+15%", "+5Hz", "+50%", "Urgent & High"),
        
        # Combo 2: Urgent Speed + Loud Pitch (-2Hz) + High Volume
        ("v3_urgent_loud", "ne-NP-HemkalaNeural", "+15%", "-2Hz", "+50%", "Urgent & Loud"),
        
        # Combo 3: Fast (slightly less than urgent) + High Pitch
        ("v3_fast_high", "ne-NP-HemkalaNeural", "+12%", "+5Hz", "+50%", "Fast & High"),
        
        # Combo 4: Fast + Loud Pitch
        ("v3_fast_loud", "ne-NP-HemkalaNeural", "+12%", "-2Hz", "+50%", "Fast & Loud"),

        # Combo 5: Very High Pitch (trying +8Hz) + Urgent
        ("v3_urgent_very_high", "ne-NP-HemkalaNeural", "+15%", "+8Hz", "+50%", "Urgent & Very High"),
    ]

    print("--- Generating V3 Voice Samples (Mix) ---")
    for name, voice, rate, pitch, vol, desc in configs:
        filename = f"automation/storage/{name}.mp3"
        print(f"Generating {desc} -> {filename} (Rate: {rate}, Pitch: {pitch}, Vol: {vol})")
        await tts_engine.generate_audio(
            text, 
            filename, 
            voice=voice, 
            rate=rate, 
            pitch=pitch,
            volume=vol
        )
    print("--- V3 Generation Complete ---")

if __name__ == "__main__":
    asyncio.run(generate_samples_v3())
