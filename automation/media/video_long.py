import os
import re
import glob
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, VideoFileClip

class VideoLongGenerator:
    def __init__(self, size=(1920, 1080)):
        self.size = size
        self.font = self._load_best_font()

    def _load_best_font(self, fsize=60):
        # Cross-Platform Font fallback list
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf", 
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf"
        ]
        font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, fsize)
                    break
                except: continue
        
        if not font and os.name != 'nt':
            for root, dirs, files in os.walk("/usr/share/fonts"):
                for file in files:
                    if file.endswith(".ttf"):
                        try:
                            font = ImageFont.truetype(os.path.join(root, file), fsize)
                            break
                        except: continue
                if font: break
        
        if not font: font = ImageFont.load_default()
        return font

    def get_pillow_text_clip(self, txt, fsize, clr, bg=None, stroke_width=2):
        try:
            # Re-load if size differs or just use loaded but this is safer for variety
            l_font = self.font if fsize == 60 else self._load_best_font(fsize)
            
            # Measure text
            dummy = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(dummy)
            bbox = draw.textbbox((0, 0), txt, font=l_font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            
            pad = 20
            img = Image.new('RGBA', (tw + pad*2, th + pad*2), (0,0,0,0))
            d = ImageDraw.Draw(img)
            
            if bg:
                d.rectangle([0, 0, tw + pad*2, th + pad*2], fill=bg)
            
            # Draw strong stroke for legibility on long videos
            if clr == 'white':
                for offset in [(-stroke_width,-stroke_width), (stroke_width,-stroke_width), 
                              (-stroke_width,stroke_width), (stroke_width,stroke_width)]:
                    d.text((pad+offset[0], pad+offset[1]), txt, font=l_font, fill='black')
            
            d.text((pad, pad), txt, font=l_font, fill=clr)
            img_np = np.array(img)
            return ImageClip(img_np)
        except Exception as e:
            print(f"Pillow Render Error (Long): {e}")
            return None

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
                    head_txt = self.get_pillow_text_clip(seg['headline'][:80], 75, 'yellow', bg=(0,0,0,180))
                    if head_txt:
                        head_txt = head_txt.set_duration(seg_duration).set_position(('center', 120))
                        bg = CompositeVideoClip([bg, head_txt], size=self.size)
                except Exception as e:
                    print(f"Header Render Error: {e}")
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
                L_HEIGHT, START_Y = 100, 750
                for l_idx, line_text in enumerate(page):
                    y_pos = START_Y + (l_idx * L_HEIGHT)
                    base_txt = self.get_pillow_text_clip(line_text, 60, 'white', bg=(0,0,0,100))
                    if base_txt:
                        base_txt = base_txt.set_start(page_start).set_duration(page_dur).set_position(('center', y_pos))
                        caption_clips.append(base_txt)
                
                # Active Highlight (Centered Bottom for current segment context)
                for off in page_offsets:
                    w_txt = self.get_pillow_text_clip(off['word'].upper(), 85, 'yellow', bg='black')
                    if w_txt:
                        w_txt = w_txt.set_duration(off['duration']).set_start(off['start']).set_position(('center', 950))
                        caption_clips.append(w_txt)
            except Exception as e:
                print(f"Daily Sync Error: {e}")
            current_word_idx += len(page_words)

        final_video = CompositeVideoClip([final_bg] + caption_clips, size=self.size).set_audio(audio)
        music_files = glob.glob("music/*.mp3") + glob.glob("automation/music/*.mp3") + glob.glob("automation/musics/news/*.mp3")
        if music_files:
            try:
                music_path = random.choice(music_files)
                from moviepy.audio.fx.all import audio_loop
                bg_music = AudioFileClip(music_path)
                # Loop the music if it's shorter than the video
                if bg_music.duration < total_duration:
                    bg_music = audio_loop(bg_music, duration=total_duration)
                else:
                    bg_music = bg_music.set_duration(total_duration)
                
                bg_music = bg_music.volumex(0.12)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.15), bg_music])
                final_video = final_video.set_audio(final_audio)
            except Exception as e:
                print(f"Music Loop Error: {e}")
                final_video = final_video.set_audio(audio)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None)
