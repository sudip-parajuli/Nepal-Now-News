from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, VideoFileClip, afx, vfx
import os
import sys
import glob
import random
import re

class VideoShortsGenerator:
    def __init__(self, size=(1080, 1920)):
        self.size = size

    def create_shorts(self, text: str, audio_path: str, output_path: str, word_offsets: list = None, media_paths: list = None, branding: dict = None, template_mode: bool = False):

        print(f"DEBUG: START create_shorts. Output: {output_path}")
        sys.stdout.flush()
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
        # Default VERY LOW for news if not specified
        music_vol = (branding or {}).get('music_volume', 0.01)
        logo_path = (branding or {}).get('logo_path', "automation/media/assets/nepal_now_logo.png")
        channel_name = (branding or {}).get('channel_name', "Nepal Now")
        
        # Initialize SFX container
        self.sfx_clips = []

        if template_mode:

            # 1. Base Layer (Background Color)
            bg_color = (branding or {}).get('bg_color', (15, 25, 45))
            bg_clips.append(ColorClip(size=self.size, color=bg_color, duration=duration))
            
            # 2. Anchor Layer (Full Screen)
            anchor_video_path = (branding or {}).get('anchor_video_path')

            anchor_added = False
            if anchor_video_path and os.path.exists(anchor_video_path):
                print(f"Adding AI Anchor video: {anchor_video_path}")
                anchor_clip = VideoFileClip(anchor_video_path)
                anchor_clip = anchor_clip.resize(height=1920)
                anchor_clip = anchor_clip.set_position('center')
                if anchor_clip.duration < duration:
                    anchor_clip = anchor_clip.fx(vfx.loop, duration=duration)
                else:
                    anchor_clip = anchor_clip.subclip(0, duration)
                bg_clips.append(anchor_clip)
                anchor_added = True
            elif os.path.exists("automation/media/assets/anchor_nepali.png") and not "science" in str(channel_name).lower():
                print("Using static AI Anchor fallback (Full Screen).")
                anchor_img = ImageClip("automation/media/assets/anchor_nepali.png").set_duration(duration)
                anchor_img = anchor_img.resize(height=1920)
                anchor_img = anchor_img.set_position('center')
                bg_clips.append(anchor_img)
                anchor_added = True

            # 3. Branding Layer (TOP LEFT) - REMOVED as per user request (logo is in anchor image)
            # if os.path.exists(logo_path):
            #     logo = ImageClip(logo_path).set_duration(duration)
            #     logo = logo.resize(height=100) # Slightly smaller for corner
            #     logo = logo.set_position((40, 40)) # Top-Left
            #     bg_clips.append(logo)
            #     
            #     if channel_name:
            #         from PIL import Image, ImageDraw, ImageFont
            #         import numpy as np
            #         
            #         font_size = 55 # Proportionate to 100px logo
            #         header_font = None
            #         possible_fonts = [
            #             "automation/media/assets/NotoSansDevanagari-Regular.ttf",
            #             "C:\\Windows\\Fonts\\arialbd.ttf"
            #         ]
            #         for pf in possible_fonts:
            #             if os.path.exists(pf):
            #                 try:
            #                     header_font = ImageFont.truetype(pf, font_size)
            #                     break
            #                 except: continue
            #         
            #         if not header_font: header_font = ImageFont.load_default()
            #         
            #         bbox = ImageDraw.Draw(Image.new('RGBA', (1, 1))).textbbox((0, 0), channel_name, font=header_font)
            #         tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            #         name_img = Image.new('RGBA', (tw + 20, th + 20), (0,0,0,0))
            #         ImageDraw.Draw(name_img).text((10, 10), channel_name, font=header_font, fill='white', stroke_width=2, stroke_fill='black')
            #         
            #         name_clip = ImageClip(np.array(name_img)).set_duration(duration)
            #         # Position next to logo (logo height is 100, x is 40 + width + padding)
            #         logo_w = logo.size[0]
            #         name_clip = name_clip.set_position((40 + logo_w + 20, 55))
            #         bg_clips.append(name_clip)
        
        elif media_paths and len(media_paths) > 0:
            transition_time = duration / len(media_paths) if len(media_paths) > 0 else 4.0
            transition_time = max(min(transition_time, 6.0), 3.0) 
            
            # Check for Science Mode early for effects
            channel_name_str = str((branding or {}).get('channel_name', "")).lower()
            is_science_mode = "science" in channel_name_str or not template_mode

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
                            # Apply Random Visual Effects
                            # USER REFREMENT: Science channel uses ONLY zoom-in
                            if is_science_mode:
                                effect_type = "zoom"
                            else:
                                effect_type = random.choice(["zoom", "static"])
                            
                            if effect_type == "zoom":
                                # Sniper Zoom: Rapid scale up
                                clip = self.apply_sniper_zoom(clip, transition_time)
                            else:
                                # Standard slow zoom
                                clip = clip.resize(lambda t: 1.0 + 0.1 * (t / transition_time))
                            
                        bg_clips.append(clip)

                        # SFX Logic
                        self._add_sfx(bg_clips, i, transition_time)

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
            # MOVED TO BOTTOM (roughly 1450 for standard 1920 height)
            FONT_SIZE, LINE_HEIGHT, MAX_CHARS_PER_LINE = 65, 100, 25
            # Layout: If template_mode (News), move to BOTTOM. Otherwise (Science), stay in CENTER.
            default_y = (self.size[1] - 470) if template_mode else ((self.size[1] // 2) - 100)
            START_Y = (branding or {}).get('caption_y', default_y)
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

            # --- SCIENCE CAPTION GENERATOR ---
            channel_name_str = str((branding or {}).get('channel_name', "")).lower()
            is_science_mode = "science" in channel_name_str or not template_mode # Default to science style if not news template
            
            if is_science_mode:
                print("DEBUG: Using Science Caption Style (Typewriter, Bold, Highlight)")
                
                # Science Font Loading (Montserrat Black or Arial Black)
                science_font = None
                science_font_size = 70 # Reduced from 80 for better visibility/margins
                
                science_font_paths = [
                    # Windows
                    "C:\\Windows\\Fonts\\arialbd.ttf",
                    "C:\\Windows\\Fonts\\ariblk.ttf",
                    "C:\\Windows\\Fonts\\impact.ttf",
                     # Linux
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
                ]
                
                # Try to load custom font if available locally
                if os.path.exists("automation/media/assets/Montserrat-Black.ttf"):
                    science_font_paths.insert(0, "automation/media/assets/Montserrat-Black.ttf")
                
                for path in science_font_paths:
                    if os.path.exists(path):
                        try:
                            science_font = ImageFont.truetype(path, science_font_size)
                            print(f"Loaded Science Font: {path}")
                            break
                        except: continue
                
                if not science_font: science_font = font # Fallback
                
                def get_science_text_clip(txt, fsize, clr, stroke_clr='black', stroke_w=6, shadow_offset=5):
                    try:
                        # Re-load font at correct size if needed, or use current
                        cur_font = science_font
                        
                        dummy = Image.new('RGB', (1, 1))
                        draw = ImageDraw.Draw(dummy)
                        bbox = draw.textbbox((0, 0), txt, font=cur_font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        
                        # Margins
                        pad = 40 # Increased padding for better margins
                        
                        # Create Image (RGBA)
                        img_w = tw + (pad * 2) + stroke_w + abs(shadow_offset)
                        img_h = th + (pad * 2) + stroke_w + abs(shadow_offset)
                        
                        img = Image.new('RGBA', (int(img_w), int(img_h)), (0,0,0,0))
                        d = ImageDraw.Draw(img)
                        
                        # Draw Position: Center
                        # Hard Drop Shadow
                        d.text((pad + shadow_offset, pad + shadow_offset), txt, font=cur_font, fill='black')
                        
                        # Strong Stroke
                        for off_x in range(-stroke_w, stroke_w+1, 2):
                             for off_y in range(-stroke_w, stroke_w+1, 2):
                                 if off_x == 0 and off_y == 0: continue
                                 d.text((pad + off_x, pad + off_y), txt, font=cur_font, fill=stroke_clr)
                        
                        # Main Text
                        d.text((pad, pad), txt, font=cur_font, fill=clr)
                        
                        return ImageClip(np.array(img))
                    except Exception as e:
                        print(f"Science Render Error: {e}")
                        return None

                # Process words for Typewriter Effect
                # 1. Group words into phrase chunks suitable for wrapping
                processed_chunks = []
                current_chunk = []
                current_len = 0
                
                for w in word_offsets:
                    word_clean = w['word']
                    
                    # Check if this word starts a new chunk (e.g. long word using content)
                    if current_len > 18 or len(current_chunk) >= 4: 
                         processed_chunks.append(current_chunk)
                         current_chunk = []
                         current_len = 0
                    
                    current_chunk.append(w)
                    current_len += len(word_clean) + 1
                    
                    # Split on punctuation
                    if word_clean.endswith(('.', '?', '!', ',')):
                        processed_chunks.append(current_chunk)
                        current_chunk = []
                        current_len = 0
                        
                if current_chunk: processed_chunks.append(current_chunk)

                for chunk in processed_chunks:
                    if not chunk: continue
                    
                    chunk_start = chunk[0]['start']
                    chunk_end = chunk[-1]['start'] + chunk[-1]['duration']
                    
                    # Ensure minimum duration for readability
                    if chunk_end - chunk_start < 0.3: chunk_end = chunk_start + 0.5
                    
                    full_text = " ".join([c['word'] for c in chunk])
                    display_text = full_text.replace('*', '')
                    
                    # WRAPPING for Safety
                    # If text is too long (over 12 chars), force a wrap to maintain side margins
                    import textwrap
                    wrapped_lines = textwrap.wrap(display_text, width=12)
                    final_display_text = "\n".join(wrapped_lines)
                    
                    is_highlight = '*' in full_text
                    text_color = '#FFD700' if is_highlight else 'white' 
                    
                    sci_clip = get_science_text_clip(final_display_text.upper(), science_font_size, text_color)
                    
                    if sci_clip:
                        sci_clip = sci_clip.set_start(chunk_start).set_duration(chunk_end - chunk_start)
                        sci_clip = sci_clip.set_position('center')
                        clips.append(sci_clip)
                        
                # --- TITLE CARD (HOOK) ---
                # Parse first sentence from text for Title if not explicitly provided?
                # For now, we don't have explicit Title input passed to this function usually.
                # We can skip strict Title Card unless we have a "title" arg.
                # But we can add the "Dong" sound at the start anyway.
                if os.path.exists("automation/media/sfx/dong.mp3"):
                     dong = AudioFileClip("automation/media/sfx/dong.mp3").set_start(0).volumex(0.8)
                     if not hasattr(self, 'sfx_clips'): self.sfx_clips = []
                     self.sfx_clips.insert(0, dong) # Ensure it's first

            else:
                # --- ORIGINAL NEWS CAPTION GENERATOR ---
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
            # Check both possible science music directories
            science_music_dirs = ["automation/music/science"]
            for sdir in science_music_dirs:
                if os.path.exists(sdir):
                    music_files.extend(glob.glob(os.path.join(sdir, "*.mp3")))
            print(f"Science Channel detected. Found {len(music_files)} music files.")
        
        # If not science, or if science music was missing (failsafe), check other folders
        # CRITICAL: If is_science is True, we DO NOT fall back to News music.
        if not is_science:
            # Check new 'news' directory
            music_files = glob.glob("automation/music/news/*.mp3") + glob.glob("automation/music/*.mp3")
            if not music_files: # Fallback to singular just in case
                music_files = glob.glob("automation/music/*.mp3")

        if music_files:
            try:
                music_path = random.choice(music_files)
                print(f"Using background music: {music_path}")
                bg_music = AudioFileClip(music_path).volumex(music_vol) # Use configured volume
                
                # Loop if too short
                if bg_music.duration < duration:
                    bg_music = bg_music.fx(afx.audio_loop, duration=duration)
                else:
                    bg_music = bg_music.subclip(0, duration)
                
                # Gentle fades (2 seconds)
                if bg_music.duration > 4:
                    bg_music = bg_music.audio_fadein(2).audio_fadeout(2)
                
                if hasattr(self, 'sfx_clips') and self.sfx_clips:
                    print(f"Adding {len(self.sfx_clips)} SFX clips to final audio.")
                    audio_components.extend(self.sfx_clips)

                from moviepy.audio.AudioClip import CompositeAudioClip
                # Boost Voice to 1.4x for clarity against music
                audio_components[0] = audio_components[0].volumex(1.4) 
                final_audio = CompositeAudioClip(audio_components)
            except Exception as e:
                print(f"Failed to load background music or SFX: {e}")
                final_audio = audio
        else:
            final_audio = audio
        print(f"DEBUG: Audio components: {len(audio_components) if 'audio_components' in locals() else 'N/A'}")
        

        final_video = CompositeVideoClip(clips, size=self.size).set_audio(final_audio).set_duration(duration)
        print(f"DEBUG: Writing video to {output_path} with duration {duration:.2f}s and {len(clips)} clips.")
        sys.stdout.flush()

        
        try:
            # Using logger=None to avoid progress bar buffering issues in some CI environments
            final_video.write_videofile(
                output_path, 
                fps=24, 
                codec="libx264", 
                audio_codec="aac", 
                threads=4, 
                preset='ultrafast', 
                logger=None 
            )
            print(f"DEBUG: Video written successfully to {output_path}")
            sys.stdout.flush()

            
            if not os.path.exists(output_path):
                 print(f"CRITICAL: write_videofile returned but file {output_path} is missing!")
                 sys.stdout.flush()

                 
        except Exception as e:
            print(f"CRITICAL ERROR writing video: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()

            raise e

    def _wrap_text(self, text, width):
        words, lines, curr = text.split(), [], []
        for w in words:
            if len(" ".join(curr + [w])) <= width: curr.append(w)
            else: lines.append(" ".join(curr)); curr = [w]
        lines.append(" ".join(curr))
        return "\n".join(lines)

    def apply_sniper_zoom(self, clip, duration):
        """Rapid zoom in (Sniper effect)."""
        # Zoom from 1.0 to 1.5 quickly over the duration
        return clip.resize(lambda t: 1.0 + (0.5 * (t / duration)**2))




    def _add_sfx(self, clips, index, clip_duration):
        """Adds SFXAudioClip if files exist."""
        sfx_dir = "automation/media/sfx"
        if not os.path.exists(sfx_dir): return

        if not clips: return
        current_clip = clips[-1]
        start_time = current_clip.start
        
        # Audio needs to be loaded
        loaded_sfx = None
        
        try:
            # 1. Riser/Dong at the very start (Index 0)
            if index == 0:
                # PRIORITIZE DONG for Science
                dong_path = os.path.join(sfx_dir, "dong.mp3")
                riser_path = os.path.join(sfx_dir, "riser.mp3")
                
                # Check if we are in science mode? Hard to tell here without context, 
                # but "dong" is generally good for hooks.
                if os.path.exists(dong_path):
                     loaded_sfx = AudioFileClip(dong_path).set_start(0).volumex(0.8)
                elif os.path.exists(riser_path):
                    loaded_sfx = AudioFileClip(riser_path).set_start(0).volumex(0.8)
            
            # 2. Transition SFX (Whoosh/Kick) for other clips
            elif index > 0:
                # Science: ALWAYS Whoosh/Slide for fast pace
                # News: Random
                
                # We'll default to high frequency for now as Shorts are fast
                whoosh_path = os.path.join(sfx_dir, "whoosh.mp3")
                
                if random.random() < 0.7: # 70% chance
                    if os.path.exists(whoosh_path) and random.random() > 0.3:
                         loaded_sfx = AudioFileClip(whoosh_path).set_start(start_time).volumex(0.6)
                    else:
                        sfx_files = [f for f in os.listdir(sfx_dir) if f.endswith('.mp3') and ('kick' in f or 'slide' in f)]
                        if sfx_files:
                            chosen_sfx = random.choice(sfx_files)
                            sfx_path = os.path.join(sfx_dir, chosen_sfx)
                            loaded_sfx = AudioFileClip(sfx_path).set_start(start_time).volumex(0.6)

            if loaded_sfx:
                if not hasattr(self, 'sfx_clips'): self.sfx_clips = []
                self.sfx_clips.append(loaded_sfx)
        
        except Exception as e:
            print(f"SFX Error: {e}")
