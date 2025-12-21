from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, VideoFileClip, afx
import os
import glob
import random
import re

class VideoShortsGenerator:
    def __init__(self, size=(1080, 1920)):
        self.size = size

    def create_shorts(self, text: str, audio_path: str, output_path: str, word_offsets: list = None, media_paths: list = None, branding: dict = None, template_mode: bool = False):
        """
        media_paths can contain both image and video file paths.
        branding: dict with keys like 'accent_color', 'bg_color', 'music_volume', 'logo_path', 'channel_name'
        """
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        bg_clips = []
        
        # Branding defaults
        accent = (branding or {}).get('accent_color', 'yellow')
        bg_overlay_color = (branding or {}).get('bg_color', (0,0,0))
        music_vol = (branding or {}).get('music_volume', 0.12)
        logo_path = (branding or {}).get('logo_path', "automation/media/assets/nepal_now_logo.png")
        channel_name = (branding or {}).get('channel_name', "Nepal Now")

        if template_mode:
            # Create a clean branded background
            bg_color = (branding or {}).get('bg_color', (15, 25, 45))
            bg_clips.append(ColorClip(size=self.size, color=bg_color, duration=duration))
            
            # Add Logo and Channel Name at the top
            if os.path.exists(logo_path):
                logo = ImageClip(logo_path).set_duration(duration).resize(width=300)
                logo = logo.set_position(('center', 150))
                bg_clips.append(logo)
            
            # Channel Name Text using Simple Overlay logic if Pillow not ready for header
            # But we have Pillow below, let's use it for the header too if needed.
            # For now, let's stick to the center captions requirement.
        
        elif media_paths and len(media_paths) > 0:
            transition_time = duration / len(media_paths) if len(media_paths) > 0 else 4.0
            transition_time = max(min(transition_time, 6.0), 3.0) 
            
            for i, m_path in enumerate(media_paths):
                if os.path.exists(m_path):
                    try:
                        is_video = m_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
                        start_time = i * transition_time
                        
                        if is_video:
                            clip = VideoFileClip(m_path).without_audio()
                            if clip.duration < transition_time:
                                clip = clip.fx(afx.loop, duration=transition_time)
                            else:
                                clip = clip.subclip(0, transition_time)
                        else:
                            clip = ImageClip(m_path).set_duration(transition_time)

                        clip = clip.set_start(start_time)
                        
                        w, h = clip.size
                        target_ratio = self.size[0]/self.size[1]
                        if w/h > target_ratio: clip = clip.resize(height=self.size[1])
                        else: clip = clip.resize(width=self.size[0])
                        clip = clip.set_position('center')
                        
                        if not is_video:
                            clip = clip.resize(lambda t: 1.05 + 0.05 * (t / transition_time))
                            
                        bg_clips.append(clip)
                    except Exception as e:
                        print(f"Error processing media {m_path}: {e}")
            
            if bg_clips:
                actual_bg_dur = sum([c.duration for c in bg_clips])
                if actual_bg_dur < duration:
                    bg_clips[-1] = bg_clips[-1].set_duration(duration - bg_clips[-1].start)
        
        if not bg_clips:
            bg_clips.append(ColorClip(size=self.size, color=(15, 15, 35), duration=duration))
        
        # 67-70: Removed the bottom overlay for cleaner look
        
        clips = bg_clips
        if word_offsets:
            print(f"DEBUG: Generating minimalist PILLOW-based karaoke captions for {len(word_offsets)} words...")
            # OPTIMIZED GEOMETRY (55pt requested, prevents clipping)
            FONT_SIZE, LINE_HEIGHT, MAX_CHARS_PER_LINE = 55, 80, 30
            START_Y = (self.size[1] // 2) - 50
            HIGHLIGHT_BG, HIGHLIGHT_TEXT, NORMAL_TEXT = accent, 'black', 'white'
            
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np

            # Load font once
            if os.name == 'nt':
                windir = os.environ.get('WINDIR', 'C:\\Windows')
                font_paths = [
                    os.path.join(windir, 'Fonts', 'Nirmala.ttc'),
                    os.path.join(windir, 'Fonts', 'aparaj.ttf'),
                    os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
                    os.path.join(windir, 'Fonts', 'NirmalaB.ttf'),
                    os.path.join(windir, 'Fonts', 'NirmalaUI.ttf'),
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
                        font = ImageFont.truetype(path, FONT_SIZE)
                        break
                    except: continue
            if not font and os.name != 'nt':
                for root, dirs, files in os.walk("/usr/share/fonts"):
                    for file in files:
                        if file.endswith(".ttf"):
                            try:
                                font = ImageFont.truetype(os.path.join(root, file), FONT_SIZE)
                                break
                            except: continue
                    if font: break
            if not font: font = ImageFont.load_default()

            def get_pillow_text_clip(txt, fsize, clr, bg=None):
                try:
                    # Measure text
                    dummy = Image.new('RGB', (1, 1))
                    draw = ImageDraw.Draw(dummy)
                    bbox = draw.textbbox((0, 0), txt, font=font)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    
                    pad = 10
                    img = Image.new('RGBA', (tw + pad*2, th + pad*2), (0,0,0,0))
                    d = ImageDraw.Draw(img)
                    if bg: d.rectangle([0, 0, tw + pad*2, th + pad*2], fill=bg)
                    if clr == 'white' and not bg:
                        for offset in [(-2,-2), (2,-2), (-2,2), (2,2)]:
                            d.text((pad+offset[0], pad+offset[1]), txt, font=font, fill='black')
                    d.text((pad, pad), txt, font=font, fill=clr)
                    img_np = np.array(img)
                    return ImageClip(img_np)
                except Exception as e:
                    print(f"Pillow Render Error: {e}")
                    return None

            lines, curr_line, curr_len = [], [], 0
            for w in word_offsets:
                if curr_len + len(w['word']) > MAX_CHARS_PER_LINE and curr_line:
                    lines.append(curr_line)
                    curr_line, curr_len = [], 0
                curr_line.append(w)
                curr_len += len(w['word']) + 1
            if curr_line: lines.append(curr_line)
            
            for line in lines:
                l_start = line[0]['start']
                l_end = line[-1]['start'] + line[-1]['duration']
                y_pos = START_Y
                
                # Devanagari doesn't have upper/lower case. Calling .upper() on it is safe but redundant.
                # However, for hybrid text, we keep it but ensure we don't break Nepali.
                line_text = " ".join([w['word'] for w in line])
                if any(ord(c) > 127 for c in line_text): # Heuristic for non-ascii (Nepali)
                    pass 
                else:
                    line_text = line_text.upper()
                try:
                    # Render full line base in white
                    base_txt = get_pillow_text_clip(line_text, FONT_SIZE, NORMAL_TEXT)
                    if base_txt:
                        base_txt = base_txt.set_start(l_start).set_duration(l_end - l_start).set_position(('center', y_pos))
                        clips.append(base_txt)
                        
                        # Calculate starting X for centering the whole line
                        line_width = base_txt.size[0]
                        current_x = (self.size[0] - line_width) // 2
                        
                        # PRECISE POSITIONING: Measure offsets for each word within the line
                        cumulative_text = ""
                        for w_idx, w_info in enumerate(line):
                            w_text = w_info['word'].upper()
                            try:
                                # Start position is the width of everything before this word
                                start_offset = font.getlength(cumulative_text)
                                # End position is width including current word
                                end_offset = font.getlength(cumulative_text + w_text)
                                
                                word_x = current_x + start_offset
                                # CALIBRATED SYNC: Add a tiny nudge (0.05s) to align with audio onset delay
                                h_start = w_info['start'] + 0.05
                                h_dur = w_info['duration']
                                
                                h_dur = w_info['duration']
                                
                                # Use original word case for highlight if Nepali
                                h_word = w_info['word']
                                if all(ord(c) < 128 for c in h_word):
                                    h_word = h_word.upper()

                                highlight = get_pillow_text_clip(h_word, FONT_SIZE, HIGHLIGHT_TEXT, bg=HIGHLIGHT_BG)
                                if highlight:
                                    # Ensure highlight width matches the measured width exactly if possible
                                    highlight = highlight.set_start(h_start).set_duration(h_dur).set_position((word_x, y_pos))
                                    clips.append(highlight)
                                
                                # Add word and space for next measurement
                                cumulative_text += h_word + " "
                            except Exception as e:
                                print(f"Word Positioning Error: {e}")
                                continue
                        print(f"DEBUG: Line sync completed for text: {line_text[:30]}...")
                except Exception as e:
                    print(f"Caption Rendering Error (Pillow): {e}")
                    continue
        else:
            print("WARNING: No word_offsets found. Using fallback text.")
            try:
                # Basic static fallback with Pillow
                msg = self._wrap_text(text, 20).upper()
                txt = get_pillow_text_clip(msg, 70, 'white', bg='black')
                if txt:
                    txt = txt.set_duration(duration).set_position('center')
                    clips.append(txt)
            except:
                pass
        
        # Prioritize dedicated music folder if provided, fallback to default music/
        music_files = []
        science_music_dir = "automation/musics/science"
        if os.path.exists(science_music_dir):
            music_files += glob.glob(os.path.join(science_music_dir, "*.mp3"))
        
        if not music_files:
            # Check plural 'musics' first
            music_files = glob.glob("music/*.mp3") + glob.glob("automation/musics/*.mp3")
            if not music_files: # Fallback to singular just in case
                music_files = glob.glob("automation/music/*.mp3")

        if music_files:
            try:
                music_path = random.choice(music_files)
                print(f"Using background music: {music_path}")
                # Ensure path is absolute for moviepy
                music_path = os.path.abspath(music_path)
                bg_music = AudioFileClip(music_path).volumex(music_vol).set_duration(duration)
                
                # Gentle fades (2 seconds)
                if bg_music.duration > 4:
                    bg_music = bg_music.audio_fadein(2).audio_fadeout(2)
                
                if bg_music.duration < duration: 
                    bg_music = bg_music.fx(afx.audio_loop, duration=duration)
                
                from moviepy.audio.AudioClip import CompositeAudioClip
                # Boost voice slightly for crystal clarity
                final_audio = CompositeAudioClip([audio.volumex(1.2), bg_music])
            except Exception as e:
                print(f"Failed to load background music: {e}")
                final_audio = audio
        else:
            final_audio = audio
        
        final_video = CompositeVideoClip(clips, size=self.size).set_audio(final_audio)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast', logger=None)

    def _wrap_text(self, text, width):
        words, lines, curr = text.split(), [], []
        for w in words:
            if len(" ".join(curr + [w])) <= width: curr.append(w)
            else: lines.append(" ".join(curr)); curr = [w]
        lines.append(" ".join(curr))
        return "\n".join(lines)
