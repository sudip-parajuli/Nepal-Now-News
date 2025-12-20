from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, concatenate_videoclips
import os
import re

class VideoLongGenerator:
    def __init__(self, size=(1920, 1080)):
        self.size = size

    def wrap_text(self, text, max_chars=40):
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(" ".join(current_line))
        return lines

    def create_daily_summary(self, segments: list, audio_path: str, output_path: str, word_offsets: list):
        """
        Creates a structured daily summary video with precise timing and centered captions.
        """
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        
        # 1. Backgrounds Construction
        bg_clips = []
        cumulative_dur = 0
        
        # We'll map each segment to its respective word offsets to get duration
        current_word_offset_idx = 0
        for i, seg in enumerate(segments):
            text_to_match = seg.get("text", "")
            if seg.get("type") == "news" and seg.get("headline"):
                text_to_match = f"{seg['headline']}। {text_to_match}"
            
            # Simple normalization for matching word counts
            words_in_seg = re.sub(r'[।.,!?]', ' ', text_to_match).split()
            num_words = len(words_in_seg)
            
            seg_offsets = word_offsets[current_word_offset_idx : current_word_offset_idx + num_words]
            if seg_offsets:
                seg_duration = (seg_offsets[-1]['start'] + seg_offsets[-1]['duration']) - seg_offsets[0]['start']
                # On the first segment, include the leading silence if any
                if i == 0:
                    seg_duration += seg_offsets[0]['start']
            else:
                seg_duration = 5 # Fallback
            
            # Ensure the last segment covers everything
            if i == len(segments) - 1:
                seg_duration = total_duration - cumulative_dur

            img_path = seg.get('image_path')
            if img_path and os.path.exists(img_path):
                bg = ImageClip(img_path).set_duration(seg_duration)
                # Resize and crop
                w, h = bg.size
                target_ratio = self.size[0]/self.size[1]
                if (w/h) > target_ratio: bg = bg.resize(height=self.size[1])
                else: bg = bg.resize(width=self.size[0])
                bg = bg.set_position('center').resize(lambda t: 1 + 0.04 * t/seg_duration)
            else:
                bg = ColorClip(size=self.size, color=(20, 20, 40), duration=seg_duration)
            
            # Add Headline Overlay for news segments
            if seg.get("type") == "news" and seg.get("headline"):
                try:
                    head_txt = TextClip(
                        seg['headline'],
                        fontsize=75,
                        color='yellow',
                        font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold',
                        bg_color='rgba(0,0,0,0.7)',
                        size=(self.size[0]-400, None),
                        method='caption'
                    ).set_duration(seg_duration).set_position(('center', 120))
                    bg = CompositeVideoClip([bg, head_txt], size=self.size)
                except: pass

            bg_clips.append(bg.set_start(cumulative_dur))
            cumulative_dur += seg_duration
            current_word_offset_idx += num_words

        final_bg = CompositeVideoClip(bg_clips, size=self.size)

        # 2. Centered Karaoke Captions (3-line pages)
        caption_clips = []
        # Re-parse segments into words to match offsets
        all_words_text = []
        for seg in segments:
            text = seg.get("text", "")
            if seg.get("type") == "news" and seg.get("headline"):
                text = f"{seg['headline']}। {text}"
            all_words_text.append(text)
        
        full_text = " ".join(all_words_text)
        lines = self.wrap_text(full_text, max_chars=40)
        pages = [lines[i:i+3] for i in range(0, len(lines), 3)]
        
        current_word_idx = 0
        for page in pages:
            page_text = " ".join(page)
            # Remove punctuation for count matching
            clean_page_text = re.sub(r'[।.,!?]', ' ', page_text)
            page_words = clean_page_text.split()
            page_offsets = word_offsets[current_word_idx : current_word_idx + len(page_words)]
            
            if not page_offsets: break
            
            page_start = page_offsets[0]['start']
            page_end = page_offsets[-1]['start'] + page_offsets[-1]['duration']
            page_dur = page_end - page_start
            
            try:
                # Dimmed base text
                base_txt = TextClip(
                    "\n".join(page),
                    fontsize=60,
                    color='white',
                    font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold',
                    method='caption',
                    size=(self.size[0]-400, 300),
                    align='Center'
                ).set_duration(page_dur).set_opacity(0.4).set_position(('center', 800)).set_start(page_start)
                
                caption_clips.append(base_txt)
                
                # Highlight active word
                for off in page_offsets:
                    # For simplicity in long video, we'll show a "Active Word" highlight at the very bottom
                    # or overlay a yellow word. Calculating exact (x,y) for centered multi-line 'caption' 
                    # is extremely hard without manual layout.
                    # Instead, we'll do a "Karaoke Line" at the bottom for the active word.
                    w_txt = TextClip(
                        off['word'],
                        fontsize=70,
                        color='yellow',
                        font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold',
                        bg_color='black'
                    ).set_duration(off['duration']).set_start(off['start']).set_position(('center', 850))
                    caption_clips.append(w_txt)
            except: pass
            
            current_word_idx += len(page_words)

        # 3. Final Assembly
        final_video = CompositeVideoClip([final_bg] + caption_clips, size=self.size)
        final_video = final_video.set_audio(audio)
        
        # Background Music
        import glob, random
        music_files = glob.glob("music/*.mp3")
        if music_files:
            bg_music_path = random.choice(music_files)
            from moviepy.audio.AudioClip import CompositeAudioClip
            bg_music = AudioFileClip(bg_music_path).volumex(0.12).set_duration(total_duration)
            final_audio = CompositeAudioClip([audio.volumex(1.15), bg_music])
            final_video = final_video.set_audio(final_audio)

        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4)
        print(f"Professional daily summary video saved to {output_path}")
