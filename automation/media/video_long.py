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

    def _load_best_font(self, fsize=60, text=""):
        # Cross-Platform Font fallback list
        is_nepali = any(ord(c) > 127 for c in text) if text else True
        
        font_paths = []
        if not is_nepali and text:
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
                    font = ImageFont.truetype(path, fsize, index=0)
                    break
                except: continue
        
        if not font and os.name != 'nt':
            for root, dirs, files in os.walk("/usr/share/fonts"):
                if font: break
                for file in files:
                    if file.endswith(".ttf"):
                        try:
                            font = ImageFont.truetype(os.path.join(root, file), fsize)
                            break
                        except: continue
        
        if not font: font = ImageFont.load_default()
        return font

    def get_pillow_text_clip(self, txt, fsize, clr, bg=None, stroke_width=2):
        try:
            # Re-load if size differs or just use loaded but this is safer for variety
            l_font = self._load_best_font(fsize, text=txt)
            
            # Measure text
            dummy = Image.new('RGB', (1, 1))
            draw = ImageDraw.Draw(dummy)
            bbox = draw.textbbox((0, 0), txt, font=l_font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            th = max(th, fsize) # Minimum height

            # Padding: 20 vertical, 90 horizontal for margins
            v_pad, h_pad = 20, 90
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
        
        # Load best font for the overall content (check first segment)
        sample_text = segments[0].get('text', '') if segments else ""
        self.font = self._load_best_font(fsize=60, text=sample_text)
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
                        # CENTERED HEADLINE: Use a slightly larger size and center middle
                        head_txt = self.get_pillow_text_clip(seg['headline'][:80], 85, 'yellow', bg=(0,0,0,200), stroke_width=3)
                        if head_txt:
                            # Position in dead center
                            head_txt = head_txt.set_duration(seg_duration).set_position('center')
                            bg = CompositeVideoClip([bg, head_txt], size=self.size)
                    except Exception as e:
                        print(f"Header Render Error: {e}")
                
                bg_clips.append(bg.set_start(cumulative_dur))
                cumulative_dur += seg_duration
        
        elif media_paths and len(media_paths) > 0:
            # Multi-media background (e.g. Science long form)
            transition_time = total_duration / len(media_paths)
            transition_time = max(min(transition_time, 6.0), 3.0) 
            
            for i, m_path in enumerate(media_paths):
                if os.path.exists(m_path):
                    try:
                        is_video = m_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
                        start_time = i * transition_time
                        if start_time >= total_duration: break
                        
                        dur = min(transition_time, total_duration - start_time)
                        # Add a small overlap for crossfade if not the last clip
                        overlap = 0.5
                        if i < len(media_paths) - 1:
                            dur += overlap
                        
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
                            # Apply a stronger zoom-in effect (1.0 to 1.15)
                            clip = clip.resize(lambda t: 1.0 + 0.15 * (t / dur))
                        
                        # Apply crossfade if not the first clip
                        if i > 0:
                            clip = clip.crossfadein(overlap)
                        
                        bg_clips.append(clip)
                    except Exception as e:
                        print(f"Error processing media {m_path}: {e}")
            
            if bg_clips:
                actual_bg_dur = sum([c.duration - overlap if i < len(bg_clips)-1 else c.duration for i, c in enumerate(bg_clips)])
                if actual_bg_dur < total_duration:
                    bg_clips[-1] = bg_clips[-1].set_duration(total_duration - bg_clips[-1].start)
        
        if not bg_clips:
            bg_clips.append(ColorClip(size=self.size, color=(15, 15, 35), duration=total_duration))

        final_bg = CompositeVideoClip(bg_clips, size=self.size)
        caption_clips = []
        
        # Word-level chunking logic (port from shorts for consistency)
        # Sentence-level chunking logic
        # 1. Reconstruct full text from offsets
        full_text = " ".join([w['word'] for w in word_offsets])
        
        # 2. Split into sentences (simple heuristic)
        import re
        # Split on .!?| but keep the delimiter attached to the previous sentence if possible, 
        # or just split and reconstruct. 
        # Regex split with capture group to keep delimiters
        sentences_raw = re.split(r'([.!?।|])', full_text)
        
        sentences = []
        current_sent = ""
        for part in sentences_raw:
            current_sent += part
            if re.match(r'[.!?।|]', part):
                sentences.append(current_sent.strip())
                current_sent = ""
        if current_sent: sentences.append(current_sent.strip())
        
        # 3. Map word offsets to sentences
        current_word_idx = 0
        sentence_chunks = []
        
        for sent_text in sentences:
            sent_words = sent_text.split()
            chunk_words = []
            matched_count = 0
            
            # Greedy match words from offsets
            while current_word_idx < len(word_offsets) and matched_count < len(sent_words):
                # We assume TTS words match loosely with script words
                # Just take the next N words corresponding to sentence length
                chunk_words.append(word_offsets[current_word_idx])
                current_word_idx += 1
                matched_count += 1
            
            if chunk_words:
                sentence_chunks.append(chunk_words)
        
        # 4. Render Sentence Captions
        FONT_SIZE = 55 # Slightly smaller for full sentences
        BOTTOM_MARGIN = 100
        
        for chunk in sentence_chunks:
            if not chunk: continue
            
            chunk_start = chunk[0]['start']
            chunk_end = chunk[-1]['start'] + chunk[-1]['duration']
            
            # Ensure minimum duration visibility (e.g. 1.5s)
            if chunk_end - chunk_start < 1.0:
                 chunk_end = chunk_start + 1.5

            chunk_text = " ".join([w['word'] for w in chunk])
            is_nepali = any(ord(c) > 127 for c in chunk_text)
            
            try:
                # Render full sentence base (White) at bottom center
                # Wrap text if too long
                wrapped_lines = self.wrap_text(chunk_text, max_chars=60)
                full_sent_text = "\n".join(wrapped_lines)
                
                base_txt = self.get_pillow_text_clip(full_sent_text, FONT_SIZE, 'white', bg=(0,0,0,180), stroke_width=2)
                
                if base_txt:
                    base_txt = base_txt.set_start(chunk_start).set_duration(chunk_end - chunk_start)
                    # Position at bottom
                    txt_w, txt_h = base_txt.size
                    pos_y = self.size[1] - txt_h - BOTTOM_MARGIN
                    base_txt = base_txt.set_position(('center', pos_y))
                    caption_clips.append(base_txt)
                    
                    # Karaoke Highlight (Yellow)
                    # We need to calculate position of each word relative to the base clip
                    # This is complex with Pillow wrapping. 
                    # SIMPLIFIED APPROACH: Just highlight the current word individually ON TOP of the base text?
                    # No, that might misalign.
                    # BETTER APPROACH: Re-render the specific word in Yellow at the *approximate* correct position?
                    # OR: Just show active word in a separate "Active" area? 
                    # User asked for: "word spoken sometimes fall behind the kareoke caption. We can show 1 sentence caption at a time... and once whole sentence read, go to next."
                    # The user implies the *sentence* should stay. The "karaoke" part (highlighting) was problematic.
                    # Let's sticking to showing the full sentence.
                    # To fix "word specific highlighting", we can try a mask or reuse the layout logic.
                    # Given complexity, let's implement the "Show 1 sentence at a time" first as a solid base.
                    # If we want highlighting, we can try to overlay the highlighted word.
                    
                    # Let's try to overlay the "current word" in Yellow. 
                    # We need exact (x,y) of the word in the wrapped text.
                    # Since wrap_text does simple logic, we can simulate layout.
                    
                    curr_x, curr_y = 90, 20 # Initial padding from get_pillow_text_clip
                    line_idx = 0
                    
                    # Re-flow to find positions
                    words_in_sent = chunk_text.split()
                    
                    # We need a font object to measure
                    l_font = self._load_best_font(FONT_SIZE, text=chunk_text)
                    
                    current_line_width = 0
                    current_line_words = []
                    
                    # Re-calculate wrapping to get lines exactly
                    wrapped_lines_words = [] 
                    temp_line = []
                    temp_len = 0
                    for w in words_in_sent:
                        if temp_len + len(w) + 1 <= 60:
                            temp_line.append(w)
                            temp_len += len(w) + 1
                        else:
                            wrapped_lines_words.append(temp_line)
                            temp_line = [w]
                            temp_len = len(w)
                    if temp_line: wrapped_lines_words.append(temp_line)
                    
                    # Now match offsets to wrapped lines
                    w_global_idx = 0
                    for l_idx, line_words in enumerate(wrapped_lines_words):
                        # Measure line width for centering correction if needed? 
                        # get_pillow_text_clip centers the text block itself on screen, but text inside is left-aligned usually?
                        # Wait, get_pillow_text_clip draws text at (h_pad, v_pad). It doesn't center align lines *internal* to the clip unless we do it.
                        # Assuming left/standard align inside the box.
                        
                        line_str = " ".join(line_words)
                        curr_x = 90 # Reset X for new line
                        curr_y = 20 + (l_idx * max(FONT_SIZE, l_font.getbbox("A")[3] - l_font.getbbox("A")[1] + 10)) # Simple line height
                        
                        for w_word in line_words:
                            if w_global_idx >= len(chunk): break
                            
                            w_info = chunk[w_global_idx]
                            w_global_idx += 1
                            
                            w_len = l_font.getlength(w_word)
                            
                            # Render Highlight Word
                            # We need absolute position on screen.
                            # Base clip pos: ('center', pos_y) -> X = (1920 - txt_w)/2, Y = pos_y
                            base_x = (self.size[0] - txt_w) // 2
                            
                            abs_x = base_x + curr_x
                            abs_y = pos_y + curr_y
                            
                            h_start = max(chunk_start, w_info['start'])
                            h_dur = w_info['duration']
                            
                            if h_dur > 0:
                                h_clip = self.get_pillow_text_clip(w_word, FONT_SIZE, 'yellow', bg=None, stroke_width=2)
                                # We need to crop/trim the padding from get_pillow_text_clip to overlay exactly?
                                # Actually get_pillow_text_clip returns a clip with padding (90, 20). 
                                # If we overlay it at (abs_x - 90, abs_y - 20), it should align perfectly IF fonts/rendering match exactly.
                                if h_clip:
                                    h_clip = h_clip.set_start(h_start).set_duration(h_dur).set_position((abs_x - 90, abs_y - 20))
                                    caption_clips.append(h_clip)
                            
                            curr_x += w_len + l_font.getlength(" ") # Advance X

            except Exception as e:
                print(f"Sentence Caption Error: {e}") 
        
        # Remove old loop variables locally to avoid confusion
        chunk = None

        final_video = CompositeVideoClip([final_bg] + caption_clips, size=self.size).set_audio(audio)
        # Use Science music exclusively if the first segment is Science
        is_science = segments and segments[0].get("type") == "science"
        music_files = []
        
        if is_science:
            # Check both possible science music directories (legacy support + new)
            science_music_dirs = ["automation/music/science"]
            for sdir in science_music_dirs:
                if os.path.exists(sdir):
                    music_files.extend(glob.glob(os.path.join(sdir, "*.mp3")))
            
            print(f"Science Video detected. Found {len(music_files)} science music files.")
            
        if not is_science:
            # News logic: Fallback through various folders
            music_files = glob.glob("automation/music/news/*.mp3") + glob.glob("automation/music/*.mp3")
        
        if music_files:
            try:
                music_path = random.choice(music_files)
                print(f"Using background music ({'SCIENCE' if is_science else 'NEWS'}): {music_path}")
                from moviepy.audio.fx.all import audio_loop
                bg_music = AudioFileClip(music_path)
                # Loop the music if it's shorter than the video
                if bg_music.duration < total_duration:
                    bg_music = audio_loop(bg_music, duration=total_duration)
                else:
                    bg_music = bg_music.set_duration(total_duration)
                
                # Dimmer volume as requested: 0.04 instead of 0.07/0.12
                bg_music = bg_music.volumex(0.04)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.15), bg_music])
                final_video = final_video.set_audio(final_audio)
            except Exception as e:
                print(f"Music Loop Error: {e}")
                final_video = final_video.set_audio(audio)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None)
