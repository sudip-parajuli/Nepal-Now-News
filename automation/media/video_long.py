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
        if os.name == 'nt':
            windir = os.environ.get('WINDIR', 'C:\\Windows')
            font_paths = [
                os.path.join(windir, 'Fonts', 'Nirmala.ttc'),
                os.path.join(windir, 'Fonts', 'aparaj.ttf'),
                os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
                os.path.join(windir, 'Fonts', 'NirmalaB.ttf'),
                os.path.join(windir, 'Fonts', 'NirmalaUI.ttf'),
                os.path.join(windir, 'Fonts', 'mangal.ttf'),
                os.path.join(windir, 'Fonts', 'utsaah.ttf'),
                os.path.join(windir, 'Fonts', 'arialbd.ttf'), 
            ]
        else:
            font_paths = [
                "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
            ]
        font = None
        for path in font_paths:
            if os.path.exists(path):
                try:
                    # Use index=0 for .ttc files
                    font = ImageFont.truetype(path, fsize, index=0)
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
            
            # Padding: 20 vertical, 50 horizontal for margins
            v_pad, h_pad = 20, 50
            img = Image.new('RGBA', (tw + h_pad*2, th + v_pad*2), (0,0,0,0))
            d = ImageDraw.Draw(img)
            
            if bg:
                d.rectangle([0, 0, tw + h_pad*2, th + v_pad*2], fill=bg)
            
            # Draw strong stroke for legibility on long videos
            if clr == 'white':
                for offset in [(-stroke_width,-stroke_width), (stroke_width,-stroke_width), 
                              (-stroke_width,stroke_width), (stroke_width,stroke_width)]:
                    d.text((h_pad+offset[0], v_pad+offset[1]), txt, font=l_font, fill='black')
            
            d.text((h_pad, v_pad), txt, font=l_font, fill=clr)
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

    def create_daily_summary(self, segments: list, audio_path: str, output_path: str, word_offsets: list, durations: list = None, template_mode: bool = False, branding: dict = None, media_paths: list = None):
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        bg_clips, cumulative_dur = [], 0
        
        logo_path = (branding or {}).get('logo_path', "automation/media/assets/nepal_now_logo.png")
        bg_color = (branding or {}).get('bg_color', (15, 25, 45))

        if template_mode:
            for i, seg in enumerate(segments):
                seg_duration = durations[i] if durations and i < len(durations) else 5
                if i == len(segments) - 1: seg_duration = total_duration - cumulative_dur
                
                bg = ColorClip(size=self.size, color=bg_color, duration=seg_duration)
                if i == 0 or i % 3 == 0: 
                     if os.path.exists(logo_path):
                        logo = ImageClip(logo_path).set_duration(seg_duration).resize(height=180)
                        logo = logo.set_position(('center', 80))
                        bg = CompositeVideoClip([bg, logo], size=self.size)
                
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
        
        elif media_paths and len(media_paths) > 0:
            # Multi-media background (e.g. Science long form)
            transition_time = total_duration / len(media_paths)
            transition_time = max(min(transition_time, 8.0), 4.0) 
            
            for i, m_path in enumerate(media_paths):
                if os.path.exists(m_path):
                    try:
                        is_video = m_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
                        start_time = i * transition_time
                        if start_time >= total_duration: break
                        
                        dur = min(transition_time, total_duration - start_time)
                        
                        if is_video:
                            clip = VideoFileClip(m_path).without_audio()
                            if clip.duration < dur:
                                from moviepy.video.fx.all import loop
                                clip = loop(clip, duration=dur)
                            else:
                                clip = clip.subclip(0, dur)
                        else:
                            clip = ImageClip(m_path).set_duration(dur)

                        clip = clip.set_start(start_time)
                        w, h = clip.size
                        target_ratio = self.size[0]/self.size[1]
                        if w/h > target_ratio: clip = clip.resize(height=self.size[1])
                        else: clip = clip.resize(width=self.size[0])
                        clip = clip.set_position('center')
                        
                        if not is_video:
                            clip = clip.resize(lambda t: 1.05 + 0.05 * (t / dur))
                        bg_clips.append(clip)
                    except Exception as e:
                        print(f"Error processing media {m_path}: {e}")
            
            if bg_clips:
                actual_bg_dur = sum([c.duration for c in bg_clips])
                if actual_bg_dur < total_duration:
                    bg_clips[-1] = bg_clips[-1].set_duration(total_duration - bg_clips[-1].start)
        
        if not bg_clips:
            bg_clips.append(ColorClip(size=self.size, color=(15, 15, 35), duration=total_duration))

        final_bg = CompositeVideoClip(bg_clips, size=self.size)
        caption_clips = []
        
        # Word-level chunking logic (5 words per chunk)
        CHUNK_SIZE = 5
        accent = (branding or {}).get('accent_color', 'yellow')
        
        for i in range(0, len(word_offsets), CHUNK_SIZE):
            chunk = word_offsets[i : i + CHUNK_SIZE]
            if not chunk: continue
            
            # Devanagari protection for line text
            line_text = " ".join([w['word'] for w in chunk])
            is_nepali = any(ord(c) > 127 for c in line_text)
            if not is_nepali:
                line_text = line_text.upper()
            
            chunk_start = chunk[0]['start']
            chunk_end = chunk[-1]['start'] + chunk[-1]['duration']
            chunk_dur = chunk_end - chunk_start
            
            try:
                # One line at a time, centered at the bottom
                y_pos = 850
                # Base line in white
                base_txt = self.get_pillow_text_clip(line_text, 65, 'white')
                if base_txt:
                    line_width = base_txt.size[0]
                    # Note: get_pillow_text_clip adds h_pad=50 (v_pad=20)
                    start_x = (self.size[0] - line_width) // 2
                    
                    base_txt = base_txt.set_start(chunk_start).set_duration(chunk_dur).set_position((start_x, y_pos))
                    caption_clips.append(base_txt)
                    
                    # Unified Highlighting: port precise positioning from shorts
                    # The text starts at start_x + 50 (due to h_pad)
                    text_start_x = start_x + 50
                    
                    cumulative_text = ""
                    for w_idx, w_info in enumerate(chunk):
                        w_text = w_info['word']
                        if not is_nepali:
                            w_text = w_text.upper()
                        
                        try:
                            start_offset = self.font.getlength(cumulative_text)
                            # Highlight clip's text should start at text_start_x + start_offset
                            # Highlight clip itself starts at (text_start_x + start_offset) - 50 
                            highlight_x = text_start_x + start_offset - 50
                            
                            h_start = w_info['start']
                            h_dur = w_info['duration']
                            
                            highlight = self.get_pillow_text_clip(w_text, 65, 'black', bg=accent)
                            if highlight:
                                highlight = highlight.set_start(h_start).set_duration(h_dur).set_position((highlight_x, y_pos))
                                caption_clips.append(highlight)
                            
                            cumulative_text += w_text + " "
                        except Exception as e:
                            print(f"Long Word Sync Error: {e}")
            except Exception as e:
                print(f"Caption Chunk Error: {e}")

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
