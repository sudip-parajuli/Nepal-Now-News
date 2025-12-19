import asyncio
import edge_tts
import os

class TTSEngine:
    default_voice = "ne-NP-HemkalaNeural"

    @staticmethod
    async def generate_audio(text: str, output_path: str, voice: str = None):
        """
        Generates high-quality Nepali narration and word-level timestamps.
        Returns: (audio_path, word_offsets)
        """
        if not voice:
            # HemkalaNeural is the standard high-quality Nepali voice
            voice = "ne-NP-HemkalaNeural"
            
        communicate = edge_tts.Communicate(text, voice, rate="+20%")
        word_offsets = []
        chunk_types = set()
        
        try:
            audio_data = bytearray()
            async for chunk in communicate.stream():
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

            with open(output_path, "wb") as f:
                f.write(audio_data)

        except Exception as e:
            print(f"Error during TTS streaming: {e}")
        
        # --- FALLBACK: Simulated Word Offsets ---
        if not word_offsets and len(text.strip()) > 0:
            print("FALLBACK: Simulated Word Sync initiated.")
            from moviepy.editor import AudioFileClip
            try:
                temp_audio = AudioFileClip(output_path)
                total_dur = temp_audio.duration
            except Exception as e:
                print(f"Warning: Could not read audio duration, estimating... ({e})")
                total_dur = len(text.split()) * 0.4 # Rough estimate
            
            try:
                words = text.split()
                start_time = 0
                total_chars = sum(len(x) for x in words)
                for w in words:
                    # Logic: use word length proportionality
                    w_dur = (len(w) / total_chars) * total_dur
                    word_offsets.append({
                        "word": w,
                        "start": start_time,
                        "duration": w_dur
                    })
                    start_time += w_dur
            except Exception as e:
                print(f"Final simulated sync attempt failed: {e}")

        if not word_offsets:
            print(f"CRITICAL: Failed to generate word offsets for synchronization.")
        else:
            print(f"SUCCESS: {len(word_offsets)} word milestones ready for animation.")
        
        return output_path, word_offsets

if __name__ == "__main__":
    # Test generation
    text = "Breaking news: A major international event is unfolding right now. More updates will follow."
    output = "test_narration.mp3"
    asyncio.run(TTSEngine.generate_audio(text, output))
