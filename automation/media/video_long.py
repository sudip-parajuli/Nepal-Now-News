from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip
import os
import re
import glob
import random

class VideoLongGenerator:
    def __init__(self, size=(1920, 1080)):
        self.size = size

    def wrap_text(self, text, max_chars=40):
        words, lines, curr, curr_len = text.split(), [], [], 0
        for w in words:
            if curr_len + len(w) + 1 <= max_chars:
                curr.append(w); curr_len += len(w) + 1
            else:
                lines.append(" ".join(curr)); curr = [w]; curr_len = len(w)
        if curr: lines.append(" ".join(curr))
        return lines

    def create_daily_summary(self, segments: list, audio_path: str, output_path: str, word_offsets: list, durations: list = None):
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        bg_clips, cumulative_dur = [], 0
        FONT = 'Nirmala-UI' if os.name == 'nt' else 'Noto-Sans-Devanagari'
        HEADER_FONT = 'Nirmala-UI-Bold' if os.name == 'nt' else 'Noto-Sans-Devanagari-Bold'

        for i, seg in enumerate(segments):
            seg_duration = durations[i] if durations and i < len(durations) else 5
            if i == len(segments) - 1: seg_duration = total_duration - cumulative_dur
            img_path = seg.get('image_path')
            if img_path and os.path.exists(img_path):
                bg = ImageClip(img_path).set_duration(seg_duration)
                w, h = bg.size
                target_ratio = self.size[0]/self.size[1]
                if (w/h) > target_ratio: bg = bg.resize(height=self.size[1])
                else: bg = bg.resize(width=self.size[0])
                bg = bg.set_position('center').resize(lambda t: 1 + 0.04 * t/seg_duration)
            else:
                bg = ColorClip(size=self.size, color=(20, 20, 40), duration=seg_duration)
            
            if seg.get("type") == "news" and seg.get("headline"):
                try:
                    head_txt = TextClip(seg['headline'], fontsize=75, color='yellow', font=HEADER_FONT, bg_color='rgba(0,0,0,0.7)', size=(self.size[0]-400, None), method='caption').set_duration(seg_duration).set_position(('center', 120))
                    bg = CompositeVideoClip([bg, head_txt], size=self.size)
                except: pass
            bg_clips.append(bg.set_start(cumulative_dur))
            cumulative_dur += seg_duration

        final_bg = CompositeVideoClip(bg_clips, size=self.size)
        caption_clips, all_words_text = [], []
        for seg in segments:
            text = seg.get("text", "")
            if seg.get("type") == "news" and seg.get("headline"): text = f"{seg['headline']}। {text}"
            all_words_text.append(text)
        
        full_text = " ".join(all_words_text)
        lines = self.wrap_text(full_text, max_chars=40)
        pages = [lines[i:i+3] for i in range(0, len(lines), 3)]
        current_word_idx = 0
        for page in pages:
            page_text = " ".join(page)
            clean_page_text = re.sub(r'[।.,!?]', ' ', page_text)
            page_words = clean_page_text.split()
            page_offsets = word_offsets[current_word_idx : current_word_idx + len(page_words)]
            if not page_offsets: break
            page_start, page_end = page_offsets[0]['start'], page_offsets[-1]['start'] + page_offsets[-1]['duration']
            page_dur = page_end - page_start
            try:
                L_HEIGHT, START_Y = 80, 750
                for l_idx, line_text in enumerate(page):
                    y_pos = START_Y + (l_idx * L_HEIGHT)
                    base_txt = TextClip(line_text, fontsize=60, color='white', font=FONT, stroke_color='black', stroke_width=1, method='label', bg_color='rgba(0,0,0,0.3)').set_start(page_start).set_duration(page_dur).set_position(('center', y_pos))
                    caption_clips.append(base_txt)
                for off in page_offsets:
                    w_txt = TextClip(off['word'], fontsize=75, color='yellow', font=HEADER_FONT, bg_color='black', method='label').set_duration(off['duration']).set_start(off['start']).set_position(('center', 1000))
                    caption_clips.append(w_txt)
            except: pass
            current_word_idx += len(page_words)

        final_video = CompositeVideoClip([final_bg] + caption_clips, size=self.size).set_audio(audio)
        music_files = glob.glob("music/*.mp3") + glob.glob("automation/music/*.mp3")
        if music_files:
            try:
                bg_music = AudioFileClip(random.choice(music_files)).volumex(0.12).set_duration(total_duration)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.15), bg_music])
                final_video = final_video.set_audio(final_audio)
            except: pass
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None)
