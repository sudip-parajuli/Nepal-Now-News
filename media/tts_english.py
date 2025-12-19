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
        # Note: we need to use stream to get metadata
        with open(output_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    # Convert microseconds to seconds
                    word_offsets.append({
                        "word": chunk["text"],
                        "start": chunk["offset"] / 10**7,
                        "duration": chunk["duration"] / 10**7
                    })
                elif chunk["type"] == "Metadata":
                    # Just for debugging
                    pass
        
        if not word_offsets:
            print("WARNING: No word boundaries were captured!")
        else:
            print(f"Audio saved to {output_path} with {len(word_offsets)} word offsets. Sample: {word_offsets[0]}")
        return output_path, word_offsets

if __name__ == "__main__":
    # Test generation
    text = "Breaking news: A major international event is unfolding right now. More updates will follow."
    output = "test_narration.mp3"
    asyncio.run(TTSEngine.generate_audio(text, output))
