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
        
        # Capture offsets while saving
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                ctype = chunk.get("type")
                if ctype == "audio":
                    f.write(chunk["data"])
                elif ctype == "WordBoundary":
                    # Convert microseconds to seconds
                    word_offsets.append({
                        "word": chunk["text"],
                        "start": chunk["offset"] / 10**7,
                        "duration": chunk["duration"] / 10**7
                    })
                elif ctype == "Metadata":
                    # Some versions might bundle offsets here
                    pass
        
        # Verify capture
        if not word_offsets:
            print(f"CRITICAL WARNING: No word boundaries were captured for text: '{text[:50]}...'. Karaoke will be disabled.")
            # Fallback check: is the text extremely short?
            if len(text.strip()) > 5:
                print("Capturing failed despite non-empty text. Check edge-tts compatibility.")
        else:
            print(f"Audio saved to {output_path} with {len(word_offsets)} word offsets. Samples: {word_offsets[:2]}")
        
        return output_path, word_offsets

if __name__ == "__main__":
    # Test generation
    text = "Breaking news: A major international event is unfolding right now. More updates will follow."
    output = "test_narration.mp3"
    asyncio.run(TTSEngine.generate_audio(text, output))
