import asyncio
import os
from automation.media.tts import TTSEngine

async def generate_samples_v2():
    # Initialize with default, but we will override params per call
    tts_engine = TTSEngine()
    
    text = """
    नमस्कार। आजको मुख्य समाचारमा स्वागत छ।
    नेपाल सरकारले नयाँ शिक्षा नीति सार्वजनिक गरेको छ।
    यसले शिक्षा क्षेत्रमा ठूलो परिवर्तन ल्याउने अपेक्षा गरिएको छ।
    """

    # Format: (Filename, Voice, Rate, Pitch, Volume, Description)
    configs = [
        # Female Variations
        ("v2_female_baseline", "ne-NP-HemkalaNeural", "+0%", "+0Hz", "+0%", "Female Baseline"),
        ("v2_female_loud", "ne-NP-HemkalaNeural", "-5%", "-2Hz", "+50%", "Female Loud & Serious"),
        ("v2_female_high", "ne-NP-HemkalaNeural", "-5%", "+5Hz", "+25%", "Female High Pitch"),
        ("v2_female_low", "ne-NP-HemkalaNeural", "-5%", "-10Hz", "+25%", "Female Low Pitch"),
        
        # Male Variations
        ("v2_male_standard", "ne-NP-SagarNeural", "+0%", "+0Hz", "+25%", "Male Standard"),
        ("v2_male_deep", "ne-NP-SagarNeural", "-5%", "-5Hz", "+25%", "Male Deep"),
    ]

    print("--- Generating V2 Voice Samples ---")
    for name, voice, rate, pitch, vol, desc in configs:
        filename = f"automation/storage/{name}.mp3"
        print(f"Generating {desc} -> {filename} (Voice: {voice}, Rate: {rate}, Pitch: {pitch}, Vol: {vol})")
        await tts_engine.generate_audio(
            text, 
            filename, 
            voice=voice, 
            rate=rate, 
            pitch=pitch,
            volume=vol
        )
    print("--- V2 Generation Complete ---")

if __name__ == "__main__":
    asyncio.run(generate_samples_v2())
