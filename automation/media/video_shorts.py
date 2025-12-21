from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, VideoFileClip, afx, vfx
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
        music_vol = (branding or {}).get('music_volume', 0.07)
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
                                clip = clip.fx(vfx.loop, duration=transition_time)
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
            # OPTIMIZED GEOMETRY (65pt for margins, smaller but cleaner)
            # Reduced MAX_CHARS_PER_LINE to 25 for better left/right margins
            FONT_SIZE, LINE_HEIGHT, MAX_CHARS_PER_LINE = 65, 100, 25
            START_Y = (self.size[1] // 2) - 100
            HIGHLIGHT_TEXT, NORMAL_TEXT = 'yellow', 'white'
            
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np

            # Load font (Cross-Platform)
            line_text_sample = " ".join([w['word'] for w in word_offsets[:10]])
            is_nepali_content = any(ord(c) > 127 for c in line_text_sample)
            
            font_paths = []
            if not is_nepali_content:
                # Prioritize English-friendly fonts for Science
                if os.name == 'nt':
                    font_paths += [
                        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf'),
                        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'segoeui.ttf'),
                    ]
                else:
                    font_paths += [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                    ]

            # Devanagari fallbacks and regular list
            font_paths += ["automation/media/assets/NotoSansDevanagari-Regular.ttf"]
            
            if os.name == 'nt':
                windir = os.environ.get('WINDIR', 'C:\\Windows')
                font_paths += [
                    os.path.join(windir, 'Fonts', 'Nirmala.ttc'),
                    os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
                    os.path.join(windir, 'Fonts', 'aparaj.ttf'),
                    os.path.join(windir, 'Fonts', 'mangal.ttf'),
                    os.path.join(windir, 'Fonts', 'arialbd.ttf'), 
                ]
            else:
                font_paths += [
                    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
                    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                ]
            
            font = None
            for path in font_paths:
                if os.path.exists(path):
                    try:
                        font = ImageFont.truetype(path, FONT_SIZE, index=0)
                        break
                    except: continue
            
            if not font and os.name != 'nt':
                # Emergency search
                for root, dirs, files in os.walk("/usr/share/fonts"):
                    if font: break
                    for file in files:
                        if file.endswith(".ttf") or file.endswith(".ttc"):
                            try:
                                font = ImageFont.truetype(os.path.join(root, file), FONT_SIZE)
                                break
                            except: continue
            
            if not font: font = ImageFont.load_default()

            def get_pillow_text_clip(txt, fsize, clr, bg=None):
                try:
                    # Measure text
                    dummy = Image.new('RGB', (1, 1))
                    draw = ImageDraw.Draw(dummy)
                    bbox = draw.textbbox((0, 0), txt, font=font)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    # Ensure minimum height for Devanagari descenders/ascenders
                    th = max(th, FONT_SIZE)
                    
                    # Padding: 10 vertical, 80 horizontal for larger margins
                    v_pad, h_pad = 10, 80
                    img = Image.new('RGBA', (tw + h_pad*2, th + v_pad*2), (0,0,0,0))
                    d = ImageDraw.Draw(img)
                    if bg: d.rectangle([0, 0, tw + h_pad*2, th + v_pad*2], fill=bg)
                    
                    # Stroke for all text for visibility
                    for offset in [(-2,-2), (2,-2), (-2,2), (2,2)]:
                        d.text((h_pad+offset[0], v_pad+offset[1]), txt, font=font, fill='black')
                    
                    d.text((h_pad, v_pad), txt, font=font, fill=clr)
                    img_np = np.array(img)
                    return ImageClip(img_np)
                except Exception as e:
                    print(f"Pillow Render Error: {e}")
                    return None

            # Wrap into lines
            lines, curr_line, curr_len = [], [], 0
            for w in word_offsets:
                if curr_len + len(w['word']) > MAX_CHARS_PER_LINE and curr_line:
                    lines.append(curr_line)
                    curr_line, curr_len = [], 0
                curr_line.append(w)
                curr_len += len(w['word']) + 1
            if curr_line: lines.append(curr_line)
            
            # Show two lines at a time
            for i in range(0, len(lines), 2):
                chunk = lines[i : i+2]
                chunk_start = chunk[0][0]['start']
                chunk_end = chunk[-1][-1]['start'] + chunk[-1][-1]['duration']
                
                for line_idx, line in enumerate(chunk):
                    # y_pos for first line vs second line
                    y_pos = START_Y + (line_idx * LINE_HEIGHT)
                    
                    line_text = " ".join([w['word'] for w in line])
                    is_nepali = any(ord(c) > 127 for c in line_text)
                    if not is_nepali:
                        line_text = line_text.upper()
                        
                    try:
                        # Render full line base in white
                        base_txt = get_pillow_text_clip(line_text, FONT_SIZE, NORMAL_TEXT)
                        if base_txt:
                            base_txt = base_txt.set_start(chunk_start).set_duration(chunk_end - chunk_start).set_position(('center', y_pos))
                            clips.append(base_txt)
                            
                            # Calculate starting X for centering the whole line
                            line_width = base_txt.size[0]
                            # get_pillow_text_clip adds h_pad=80
                            text_start_x = (self.size[0] - line_width) // 2 + 80
                            
                            cumulative_text = ""
                            for w_info in line:
                                w_text = w_info['word']
                                if not is_nepali:
                                    w_text = w_text.upper()
                                
                                try:
                                    l_font = font # Reuse already loaded best font
                                    start_offset = l_font.getlength(cumulative_text)
                                    word_x = text_start_x + start_offset - 80 # Adjust for h_pad
                                    
                                    h_start = max(0, w_info['start'] - 0.05)
                                    h_dur = w_info['duration'] + 0.1

                                    # HIGHLIGHT: Yellow color instead of red background
                                    highlight = get_pillow_text_clip(w_text, FONT_SIZE, HIGHLIGHT_TEXT)
                                    if highlight:
                                        highlight = highlight.set_start(h_start).set_duration(h_dur).set_position((word_x, y_pos))
                                        clips.append(highlight)
                                    
                                    cumulative_text += w_text + " "
                                except Exception as e:
                                    print(f"Word Positioning Error: {e}")
                                    continue
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
        
        # Exclusively use Science music if channel_name suggests it
        music_files = []
        is_science = "science" in str(channel_name).lower()
        
        if is_science:
            science_music_dir = "automation/musics/science"
            if os.path.exists(science_music_dir):
                music_files = glob.glob(os.path.join(science_music_dir, "*.mp3"))
            print(f"Science Channel detected. Found {len(music_files)} music files in {science_music_dir}")
        
        # If not science, or if science music was missing (failsafe), check other folders
        # CRITICAL: If is_science is True, we DO NOT fall back to News music.
        if not music_files and not is_science:
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
