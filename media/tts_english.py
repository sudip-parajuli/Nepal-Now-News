import asyncio
import edge_tts
import os

class TTSEngine:
    default_voice = "en-US-ChristopherNeural"

    @staticmethod
    async def generate_audio(text: str, output_path: str, voice: str = None):
        """
        Generates high-quality English narration and word-level timestamps.
        Returns: (audio_path, word_offsets)
        """
        if not voice:
            voice = TTSEngine.default_voice
            
        communicate = edge_tts.Communicate(text, voice)
        
        word_offsets = []
        # Capture offsets while saving
        try:
            with open(output_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        word_offsets.append({
                            "word": chunk["text"],
                            "start": chunk["offset"] / 10**7,
                            "duration": chunk["duration"] / 10**7
                        })
        except Exception as e:
            print(f"Error during TTS streaming: {e}")
        
        # Verify capture
        if not word_offsets:
            print(f"CRITICAL WARNING: No word boundaries captured for '{text[:30]}...'")
            print("This could be due to edge-tts version or voice compatibility.")
        else:
            print(f"Audio saved to {output_path} with {len(word_offsets)} word offsets.")
        
        return output_path, word_offsets

if __name__ == "__main__":
    # Test generation
    text = "Breaking news: A major international event is unfolding right now. More updates will follow."
    output = "test_narration.mp3"
    asyncio.run(TTSEngine.generate_audio(text, output))
