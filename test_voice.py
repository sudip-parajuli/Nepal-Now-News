import asyncio
import os
from automation.media.tts import TTSEngine

async def test_voice():
    tts = TTSEngine(
        voice_map={"female": "ne-NP-HemkalaNeural"},
        rate="-5%",
        pitch="-2Hz"
    )
    
    text = """
नमस्कार।
तपाईं हेर्दै हुनुहुन्छ
आजको मुख्य समाचार।

आज नेपाल सरकारले
नयाँ शिक्षा नीति
सार्वजनिक गरेको छ।

सरकारका अनुसार,
यो नीतिले
शिक्षा क्षेत्रमा
सुधार ल्याउनेछ।

विस्तृत समाचारका लागि
हाम्रो च्यानलसँगै रहनुहोस्।
    """
    
    output_path = "automation/storage/test_voice_output.mp3"
    print(f"Generating audio to: {output_path}")
    await tts.generate_audio(text, output_path, voice="ne-NP-HemkalaNeural")
    print("Done.")

if __name__ == "__main__":
    asyncio.run(test_voice())
