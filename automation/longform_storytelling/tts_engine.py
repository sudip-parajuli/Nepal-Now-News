import asyncio
import os
from typing import List, Dict
from automation.media.tts import TTSEngine

class StoryTTSEngine(TTSEngine):
    def __init__(self):
        super().__init__()
        # Distinct parameters for Baje and Arav using the same male voice
        self.baje_voice = "ne-NP-SagarNeural"
        self.baje_rate = "-10%"
        self.baje_pitch = "-12Hz"
        
        self.arav_voice = "ne-NP-SagarNeural"
        self.arav_rate = "+15%"
        self.arav_pitch = "+0Hz"

    async def generate_story_audio(self, script: List[Dict], output_path: str):
        """
        Generates audio for the script with distinct character voices.
        """
        all_offsets = []
        cumulative_duration = 0
        temp_audio_files = []
        
        for i, line in enumerate(script):
            temp_path = f"automation/storage/temp_story_{i}.mp3"
            
            if line['speaker'] == "बाजे":
                voice, rate, pitch = self.baje_voice, self.baje_rate, self.baje_pitch
            else:
                voice, rate, pitch = self.arav_voice, self.arav_rate, self.arav_pitch
            
            _, offsets = await self.generate_audio(line['text'], temp_path, voice, rate=rate, pitch=pitch)
            
            from moviepy.editor import AudioFileClip
            try:
                clip = AudioFileClip(temp_path)
                dur = clip.duration
                
                # Update offsets with cumulative start time
                for off in offsets:
                    off["start"] += cumulative_duration
                    all_offsets.append(off)
                
                # Store line-specific offsets for the video generator
                line['word_offsets'] = offsets
                line['audio_duration'] = dur
                line['audio_start'] = cumulative_duration
                
                cumulative_duration += dur
                temp_audio_files.append(temp_path)
                clip.close()
            except Exception as e:
                print(f"Error processing audio segment {i}: {e}")

        # Concatenate audio files
        from moviepy.editor import concatenate_audioclips, AudioFileClip
        clips = [AudioFileClip(f) for f in temp_audio_files]
        final_audio = concatenate_audioclips(clips)
        final_audio.write_audiofile(output_path, fps=44100, logger=None)
        
        for c in clips: c.close()
        for f in temp_audio_files:
            try: os.remove(f)
            except: pass

        return output_path, all_offsets, script

if __name__ == "__main__":
    # Test
    async def test():
        engine = StoryTTSEngine()
        test_script = [
            {"speaker": "बाजे", "text": "ओए आरव, के छ खबर?"},
            {"speaker": "आरव", "text": "सब ठीक छ बाजे, तपाईँको गफ सुन्न आएको!"}
        ]
        await engine.generate_story_audio(test_script, "automation/storage/test_story.mp3")
    
    asyncio.run(test())
