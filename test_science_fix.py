import asyncio
import os
from automation.media.tts import TTSEngine
from automation.media.video_shorts import VideoShortsGenerator

async def test_science_aesthetics():
    # 1. Test TTS with calm settings
    tts = TTSEngine(rate="-25%", pitch="-12Hz")
    output_audio = "automation/storage/test_science_audio.mp3"
    text = "The universe is a vast and mysterious place, filled with wonders we are only beginning to understand."
    voice = "en-US-ChristopherNeural"
    
    print(f"Generating audio with {voice} at -25% rate and -12Hz pitch...")
    _, offsets = await tts.generate_audio(text, output_audio, voice=voice)
    
    if os.path.exists(output_audio):
        print(f"SUCCESS: Audio generated at {output_audio}")
    else:
        print("FAILURE: Audio not generated")

    # 2. Test Font Selection
    vgen = VideoShortsGenerator()
    output_video = "automation/storage/test_science_font.mp4"
    
    # We'll just trigger the font loading part by calling create_shorts in a mock way
    # Or just check if it finds the right font.
    # Since we can't easily "see" the video here, we'll trust the logic if it runs without error.
    
    print("Testing video generation with English text (checking for font errors)...")
    try:
        # Template mode avoids media fetching
        vgen.create_shorts(
            text, 
            output_audio, 
            output_video, 
            word_offsets=offsets, 
            template_mode=True,
            branding={'bg_color': (0,0,0)}
        )
        print(f"SUCCESS: Video generated at {output_video}")
    except Exception as e:
        print(f"FAILURE: Video generation failed: {e}")

if __name__ == "__main__":
    if not os.path.exists("automation/storage"):
        os.makedirs("automation/storage")
    asyncio.run(test_science_aesthetics())
