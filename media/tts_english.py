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
        chunk_types = set()
        try:
            # We'll collect all chunks first into memory to ensure we don't block the stream
            # but for very long summaries, we should still write audio incrementally.
            # Let's do a hybrid: write audio, but keep metadata.
            audio_data = bytearray()
            
            async for chunk in communicate.stream():
                # Some versions use 'type', others 'Type'. Let's be safe.
                ctype = chunk.get("type") or chunk.get("Type") or "unknown"
                chunk_types.add(ctype)
                
                if ctype == "audio":
                    audio_data.extend(chunk["data"])
                elif ctype == "WordBoundary":
                    word_offsets.append({
                        "word": chunk.get("text") or chunk.get("Text"),
                        "start": (chunk.get("offset") or chunk.get("Offset")) / 10**7,
                        "duration": (chunk.get("duration") or chunk.get("Duration")) / 10**7
                    })
                elif ctype == "Metadata":
                    # Check if word boundaries are inside metadata (rare but possible in some versions)
                    if "text" in chunk and "offset" in chunk:
                         word_offsets.append({
                            "word": chunk["text"],
                            "start": chunk["offset"] / 10**7,
                            "duration": chunk["duration"] / 10**7
                        })

            with open(output_path, "wb") as f:
                f.write(audio_data)

        except Exception as e:
            print(f"Error during TTS streaming: {e}")
        
        # Verify capture
        if not word_offsets:
            print(f"CRITICAL WARNING: No word boundaries captured for '{text[:30]}...'")
            print(f"Captured chunk types: {chunk_types}")
            print("Possible causes: Voice incompatibility, edge-tts version mismatch, or network packet loss in GHA.")
        else:
            print(f"SUCCESS: Captured {len(word_offsets)} word boundaries for synchronization.")
        
        return output_path, word_offsets

if __name__ == "__main__":
    # Test generation
    text = "Breaking news: A major international event is unfolding right now. More updates will follow."
    output = "test_narration.mp3"
    asyncio.run(TTSEngine.generate_audio(text, output))
