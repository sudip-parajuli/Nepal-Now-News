import asyncio
import edge_tts
import os
import re
from typing import List, Dict

class TTSEngine:
    def __init__(self, voice_map=None, rate="+20%"):
        self.voice_map = voice_map or {
            "female": "ne-NP-HemkalaNeural",
            "male": "ne-NP-SagarNeural"
        }
        self.rate = rate

    async def generate_multivocal_audio(self, segments: List[Dict], output_path: str):
        """
        Generates audio for multiple segments with alternating voices and merges offsets.
        Returns: (output_path, word_offsets, segment_durations)
        """
        all_offsets = []
        segment_durations = []
        cumulative_duration = 0
        temp_audio_files = []
        
        for i, seg in enumerate(segments):
            temp_path = f"automation/storage/temp_seg_{i}.mp3"
            voice = self.voice_map.get(seg.get("gender"), self.voice_map.get("female"))
            
            text_to_speak = seg.get("text", "")
            if seg.get("type") == "news" and seg.get("headline"):
                text_to_speak = f"{seg['headline']}। {text_to_speak}"
            
            _, offsets = await self.generate_audio(text_to_speak, temp_path, voice)
            
            for off in offsets:
                off["start"] += cumulative_duration
                all_offsets.append(off)
            
            from moviepy.editor import AudioFileClip
            clip = AudioFileClip(temp_path)
            dur = clip.duration
            segment_durations.append(dur)
            cumulative_duration += dur
            temp_audio_files.append(temp_path)
            clip.close()

        from moviepy.editor import concatenate_audioclips, AudioFileClip
        clips = [AudioFileClip(f) for f in temp_audio_files]
        final_audio = concatenate_audioclips(clips)
        final_audio.write_audiofile(output_path, fps=44100, logger=None)
        
        for c in clips: c.close()
        for f in temp_audio_files: 
            try: os.remove(f)
            except: pass

        return output_path, all_offsets, segment_durations

    async def generate_audio(self, text: str, output_path: str, voice: str = None):
        text = text.strip()
        
        # Detection: If text contains Devanagari, apply Nepali normalization
        if re.search(r'[\u0900-\u097F]', text):
            abbreviations = {
                r'डा\.': 'डाक्टर',
                r'इ\.': 'इन्जिनियर',
                r'ई\.': 'इन्जिनियर',
                r'प्रा\.': 'प्राध्यापक',
                r'प\.': 'पण्डित',
                r'वि\.सं\.': 'विक्रम सम्बत',
                r'नं\.': 'नम्बर',
                r'कि\.मी\.': 'किलोमिटर',
                r'मि\.': 'मिटर'
            }
            for abbr, full in abbreviations.items():
                text = re.sub(abbr, full, text)
            text = re.sub(r'([।.,!?])(?=[^\s])', r'\1 ', text)
        else:
            # English specific normalization if needed (e.g., standardizing Dr. etc)
            text = re.sub(r'([.,!?])(?=[^\s])', r'\1 ', text)

        text = re.sub(r'\s+', ' ', text)
        
        if not text:
            return output_path, []

        voice = voice or self.voice_map.get("female")
        print(f"DEBUG: TTSEngine communicating with voice: {voice}")
        communicate = edge_tts.Communicate(text, voice, rate=self.rate)
        word_offsets = []
        
        try:
            audio_data = bytearray()
            async for chunk in communicate.stream():
                ctype = chunk.get("type") or chunk.get("Type") or "unknown"
                if ctype == "audio":
                    audio_data.extend(chunk["data"])
                elif ctype == "WordBoundary":
                    word_offsets.append({
                        "word": chunk.get("text") or chunk.get("Text"),
                        "start": (chunk.get("offset") or chunk.get("Offset")) / 10**7,
                        "duration": (chunk.get("duration") or chunk.get("Duration")) / 10**7
                    })

            if audio_data:
                with open(output_path, "wb") as f:
                    f.write(audio_data)
        except Exception as e:
            print(f"Error during TTS streaming: {e}")
        
        if not word_offsets and len(text.strip()) > 0:
            from moviepy.editor import AudioFileClip
            try:
                temp_audio = AudioFileClip(output_path)
                total_dur = temp_audio.duration
                temp_audio.close()
            except:
                total_dur = len(text.split()) * 0.4
            
            words = text.split()
            start_time = 0
            total_chars = sum(len(x) for x in words)
            for w in words:
                w_dur = (len(w) / total_chars) * total_dur
                word_offsets.append({"word": w, "start": start_time, "duration": w_dur})
                start_time += w_dur

        return output_path, word_offsets
