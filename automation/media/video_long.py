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
            
            import math
            required_clips = math.ceil(total_duration / transition_time) + 1
            extended_media_paths = []
            while len(extended_media_paths) < required_clips:
                extended_media_paths.extend(media_paths)
            
            for i, m_path in enumerate(extended_media_paths):
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
                        
                        # Add Transition SFX (Whoosh)
                        # We don't have a dedicated SFX track in this generator yet, 
                        # so we need to mix it into audio later or composite it here?
                        # `VideoLongGenerator` structure separates audio mix at the end.
                        # We'll collect SFX timestamps and mix them later.
                        if not hasattr(self, 'sfx_events'): self.sfx_events = []
                        if i > 0:
                             self.sfx_events.append({'time': start_time, 'file': 'whoosh.mp3'})

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
        
        # ── Font: Heavy/Extra-Bold sans-serif ─────────────────────────────────
        POP_FONT_SIZE = 95
        pop_font = None
        pop_font_paths = [
            "automation/media/assets/Montserrat-Black.ttf",
            "automation/media/assets/Montserrat-ExtraBold.ttf",
            "C:\\Windows\\Fonts\\ariblk.ttf",
            "C:\\Windows\\Fonts\\impact.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        ]
        for _fp in pop_font_paths:
            if os.path.exists(_fp):
                try:
                    pop_font = ImageFont.truetype(_fp, POP_FONT_SIZE)
                    break
                except: continue
        if not pop_font:
            pop_font = self.font
            
        # ── Keyword detection ─────────────────────────────────────────────────
        _STOP = {
            'the','a','an','is','are','was','were','be','been','being',
            'of','in','on','at','to','for','and','or','but','so','yet',
            'it','its','this','that','these','those','with','from','by',
            'as','into','do','does','did','not','no','have','has','had',
            'will','would','can','could','should','may','might','what',
            'which','who','when','where','why','how','if','than','then',
            'there','here','they','we','he','she','you','i','my','your',
            'our','their','his','her','also','just','even','up','out',
            'about','over','more','very','such','each',
        }

        def _is_keyword(w):
            clean = re.sub(r'[^a-zA-Z0-9]', '', w).lower()
            if not clean: return False
            if clean in _STOP: return False
            if '*' in w: return True
            if len(clean) >= 6: return True
            return False

        # ── Render one chunk as RGBA PIL image with per-word colors ──────────
        def _render_popup(words_list, highlight_mask):
            STROKE = 4
            SHADOW = 5
            HP, VP = 32, 26
            MAX_W = 1600 # Safe width for 1080p long form landscape

            dummy = Image.new('RGB', (1, 1))
            dd = ImageDraw.Draw(dummy)
            sp_bbox = dd.textbbox((0, 0), " ", font=pop_font)
            sp_w = max(sp_bbox[2] - sp_bbox[0], 12)

            lines = []
            current_line = []
            current_w = 0
            max_h = 0
            
            for idx, wrd in enumerate(words_list):
                bb = dd.textbbox((0, 0), wrd, font=pop_font)
                ww, wh = bb[2]-bb[0], bb[3]-bb[1]
                max_h = max(max_h, wh)
                
                if current_line and current_w + ww + sp_w > MAX_W:
                    lines.append(current_line)
                    current_line = []
                    current_w = 0
                    
                current_line.append((idx, wrd, ww, wh))
                current_w += ww + sp_w if current_line else ww
            
            if current_line:
                lines.append(current_line)

            line_widths = []
            for line in lines:
                lw = sum(w[2] for w in line) + sp_w * (max(len(line) - 1, 0))
                line_widths.append(lw)
            
            total_w = max(line_widths) if line_widths else 0
            total_h = len(lines) * max_h + max(len(lines) - 1, 0) * 10
            
            img_w = int(total_w + HP*2 + STROKE*2 + SHADOW + 4)
            img_h = int(total_h + VP*2 + STROKE*2 + SHADOW + 4)

            img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            
            y = VP + STROKE
            for line_idx, line in enumerate(lines):
                line_w = line_widths[line_idx]
                x = (img_w - line_w) // 2
                
                for idx, wrd, ww, _ in line:
                    clr = '#FFD700' if highlight_mask[idx] else 'white'
                    d.text((x+SHADOW, y+SHADOW), wrd, font=pop_font, fill=(0,0,0,160))
                    for dx in range(-STROKE, STROKE+1):
                        for dy in range(-STROKE, STROKE+1):
                            if dx == 0 and dy == 0: continue
                            d.text((x+dx, y+dy), wrd, font=pop_font, fill='black')
                    d.text((x, y), wrd, font=pop_font, fill=clr)
                    x += ww + sp_w
                y += max_h + 10
                
            return img

        # ── Group word_offsets into 2-3 word chunks ───────────────────────────
        pop_chunks = []
        cur_chunk, cur_len = [], 0
        for w in word_offsets:
            wclean = re.sub(r'\[.*?\]', '', w['word'].replace('*', '')).strip()
            if not wclean: continue
            if cur_len >= 3 or (cur_len >= 2 and wclean.endswith(('.','?','!',','))):
                pop_chunks.append(cur_chunk)
                cur_chunk, cur_len = [], 0
            cur_chunk.append({**w, 'display': wclean})
            cur_len += 1
            if wclean.endswith(('.', '?', '!')):
                pop_chunks.append(cur_chunk)
                cur_chunk, cur_len = [], 0
        if cur_chunk:
            pop_chunks.append(cur_chunk)

        # ── Render each chunk with 80→100% scale-in pop animation ─────────────
        for i, chunk in enumerate(pop_chunks):
            if not chunk: continue
            chunk_start = chunk[0]['start']
            
            if i < len(pop_chunks) - 1 and pop_chunks[i+1]:
                next_start = pop_chunks[i+1][0]['start']
                chunk_dur = max(next_start - chunk_start, 0.1)
            else:
                chunk_end = chunk[-1]['start'] + chunk[-1]['duration']
                chunk_dur = max(chunk_end - chunk_start, 0.35)

            words_display = [c['display'].upper() for c in chunk]
            hi_mask       = [_is_keyword(c['word']) for c in chunk]

            try:
                pil_img  = _render_popup(words_display, hi_mask)
                pop_clip = ImageClip(np.array(pil_img))
                anim_dur = min(0.18, chunk_dur * 0.35)
                pop_clip = pop_clip.resize(
                    lambda t, ad=anim_dur: min(1.0, 0.80 + 0.20 * (t / ad))
                )
                pop_clip = pop_clip.set_start(chunk_start).set_duration(chunk_dur).set_position('center')
                caption_clips.append(pop_clip)
            except Exception as e:
                print(f"PopUp render error: {e}")
                continue

        final_video = CompositeVideoClip([final_bg] + caption_clips, size=self.size).set_audio(audio)
        
        music_files = []
        science_music_dirs = ["automation/music/science"]
        for sdir in science_music_dirs:
            if os.path.exists(sdir):
                music_files.extend(glob.glob(os.path.join(sdir, "*.mp3")))
        
        print(f"Science Video detected. Found {len(music_files)} science music files.")
        
        if music_files:
            try:
                music_path = random.choice(music_files)
                print(f"Using background music: {music_path}")
                from moviepy.audio.fx.all import audio_loop
                bg_music = AudioFileClip(music_path)
                # Loop the music if it's shorter than the video
                if bg_music.duration < total_duration:
                    bg_music = audio_loop(bg_music, duration=total_duration)
                else:
                    bg_music = bg_music.set_duration(total_duration)
                
                # Dimmer volume as requested: 0.04 instead of 0.07/0.12
                # Dimmer volume as requested: 0.04 instead of 0.07/0.12
                bg_music = bg_music.volumex(0.04)
                
                audio_mix = [audio.volumex(1.15), bg_music]
                
                # Add gathered SFX
                if hasattr(self, 'sfx_events') and self.sfx_events:
                     sfx_dir = "automation/media/sfx"
                     for event in self.sfx_events:
                         sfx_file = event['file']
                         sfx_path = os.path.join(sfx_dir, sfx_file)
                         if os.path.exists(sfx_path):
                             sfx_clip = AudioFileClip(sfx_path).set_start(event['time']).volumex(0.5)
                             audio_mix.append(sfx_clip)

                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip(audio_mix)
                final_video = final_video.set_audio(final_audio)
            except Exception as e:
                print(f"Music Loop Error: {e}")
                final_video = final_video.set_audio(audio)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, logger=None)
