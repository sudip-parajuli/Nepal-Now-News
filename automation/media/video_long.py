import os
import re
import glob
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, VideoFileClip

from .scene_renderer import SceneRenderer

def calculate_adjusted_durations(scenes, fps=30) -> list[float]:
    """
    Correction 2 standalone function:
    Calculates adjusted visual scene durations accounting for transitions.
    Formula:
    - Each flash adds 2/fps = 0.0667s to total duration
    - Each fade removes fade_overlap_seconds (0.5s)
    """
    durations = []
    transitions = []
    for i in range(len(scenes) - 1):
        next_type = scenes[i+1].get("visual_type")
        curr_type = scenes[i].get("visual_type")
        if next_type in ("hook_question", "kinetic_stat"):
            transitions.append("flash")
        elif (curr_type == "image" and next_type == "ai_video") or (curr_type == "ai_video" and next_type == "image"):
            transitions.append("fade")
        else:
            transitions.append("cut")
            
    for i, scene in enumerate(scenes):
        base_dur = 5.0 # default base visual duration if none specified
        before_t = transitions[i-1] if i > 0 else None
        after_t = transitions[i] if i < len(transitions) else None
        
        adj_dur = base_dur
        if before_t == "fade":
            adj_dur += 0.5
        if after_t == "flash":
            adj_dur += 0.0667
        durations.append(adj_dur)
    return durations

def match_scenes_to_timestamps(scenes, word_offsets, total_duration):
    """
    Sequentially matches each scene's narration words to the continuous list of word_offsets.
    Returns a list of dicts: {"start": float, "end": float, "duration": float, "word_times": list[float]}.
    """
    def clean_word(w):
        return re.sub(r'[^a-zA-Z0-9]', '', w).lower()
        
    cleaned_offsets = [clean_word(w["word"]) for w in word_offsets]
    current_offset_idx = 0
    num_offsets = len(word_offsets)
    scene_timings = []
    
    for idx, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        scene_words = [clean_word(w) for w in narration.split() if clean_word(w)]
        if not scene_words or not word_offsets:
            scene_timings.append({
                "start": idx * (total_duration / len(scenes)),
                "end": (idx + 1) * (total_duration / len(scenes)),
                "word_times": [0.0]
            })
            continue
            
        start_time = None
        matched_offsets_indices = []
        for sw in scene_words:
            found = False
            for j in range(current_offset_idx, min(current_offset_idx + 100, num_offsets)):
                if cleaned_offsets[j] == sw:
                    matched_offsets_indices.append(j)
                    current_offset_idx = j + 1
                    found = True
                    break
            if not found:
                if current_offset_idx < num_offsets:
                    matched_offsets_indices.append(current_offset_idx)
                    current_offset_idx += 1
                    
        if matched_offsets_indices:
            start_time = word_offsets[matched_offsets_indices[0]]["start"]
            last_w = word_offsets[matched_offsets_indices[-1]]
            end_time = last_w["start"] + last_w["duration"]
            word_times = [word_offsets[idx]["start"] - start_time for idx in matched_offsets_indices]
        else:
            start_time = current_offset_idx / max(1, num_offsets) * total_duration
            end_time = (current_offset_idx + len(scene_words)) / max(1, num_offsets) * total_duration
            word_times = [0.0] * len(scene_words)
            
        scene_timings.append({
            "start": start_time,
            "end": end_time,
            "word_times": word_times
        })
        
    # Calibrate starts/ends sequentially to guarantee absolute coverage
    if scene_timings:
        scene_timings[0]["start"] = 0.0
        for i in range(1, len(scene_timings)):
            prev_end = scene_timings[i-1]["end"]
            scene_timings[i]["start"] = prev_end
            if scene_timings[i]["end"] <= prev_end:
                scene_timings[i]["end"] = prev_end + 3.0
        scene_timings[-1]["end"] = total_duration
        
    for item in scene_timings:
        item["duration"] = max(0.1, item["end"] - item["start"])
        
    return scene_timings

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

    def _render_kinetic_stat_clip(self, kinetic_stat: dict, duration: float):
        """
        Renders a full-screen count-up stat slide using MoviePy's VideoClip(make_frame).
        The number counts up from 0 to its final value over the first 80% of duration.
        """
        from moviepy.editor import VideoClip

        value    = kinetic_stat.get("value", 0)
        unit     = kinetic_stat.get("unit", "")
        label    = kinetic_stat.get("label", "")
        w, h     = self.size

        # Fonts — big bold for value, smaller for unit/label
        val_font = self._load_best_font(fsize=160)
        unit_font = self._load_best_font(fsize=72)
        lbl_font  = self._load_best_font(fsize=48)

        def make_frame(t):
            # Ease-out interpolation: accelerate quickly then settle
            progress = min(t / max(duration * 0.80, 0.01), 1.0)
            ease     = 1.0 - (1.0 - progress) ** 3   # cubic ease-out
            current  = int(ease * value)

            img  = Image.new("RGB", (w, h), (8, 8, 22))   # deep space dark
            draw = ImageDraw.Draw(img)

            # Subtle horizontal gradient bar accent
            for x in range(w):
                alpha = int(30 * abs(x / w - 0.5) * 2)
                draw.line([(x, h // 2 - 130), (x, h // 2 + 130)],
                          fill=(30 + alpha, 10, 60 + alpha))

            # Value number  (centred)
            val_str  = f"{current:,}"
            v_bbox   = draw.textbbox((0, 0), val_str, font=val_font)
            vw, vh   = v_bbox[2] - v_bbox[0], v_bbox[3] - v_bbox[1]
            vx       = (w - vw) // 2
            vy       = h // 2 - vh // 2 - 40
            # Shadow
            draw.text((vx + 4, vy + 4), val_str, font=val_font, fill=(0, 0, 0, 180))
            draw.text((vx, vy), val_str, font=val_font, fill=(245, 195, 50))

            # Unit  (right of value, vertically centred)
            u_bbox = draw.textbbox((0, 0), unit, font=unit_font)
            uw     = u_bbox[2] - u_bbox[0]
            ux     = vx + vw + 18
            uy     = vy + vh - (u_bbox[3] - u_bbox[1]) - 6
            draw.text((ux, uy), unit, font=unit_font, fill=(200, 200, 255))

            # Label  (below)
            l_bbox = draw.textbbox((0, 0), label.upper(), font=lbl_font)
            lx     = (w - (l_bbox[2] - l_bbox[0])) // 2
            ly     = vy + vh + 28
            draw.text((lx, ly), label.upper(), font=lbl_font, fill=(140, 140, 180))

            return np.array(img)

        return VideoClip(make_frame, duration=duration).set_fps(24)

    def _render_kinetic_text_overlay_clip(self, base_image_path: str,
                                          kinetic_stat: dict, duration: float):
        """
        Returns a CompositeVideoClip: base image (Ken Burns) + lower-third
        animated stat overlay.  Falls back to full-screen stat if no image.
        """
        from moviepy.editor import ImageClip, CompositeVideoClip, VideoClip

        value = kinetic_stat.get("value", 0) if kinetic_stat else None
        unit  = kinetic_stat.get("unit", "") if kinetic_stat else ""
        label = kinetic_stat.get("label", "") if kinetic_stat else ""
        w, h  = self.size

        # ── Base image with Ken Burns ─────────────────────────────────────────
        try:
            with Image.open(base_image_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                base_clip = ImageClip(np.array(img)).set_duration(duration)
            iw, ih = base_clip.size
            ratio  = w / h
            if iw / ih > ratio: base_clip = base_clip.resize(height=h)
            else:               base_clip = base_clip.resize(width=w)
            base_clip = base_clip.set_position("center")
            base_clip = base_clip.resize(lambda t: 1.0 + 0.04 * (t / duration))
        except Exception as e:
            print(f"[VideoLong] Overlay base image error: {e}. Using full-screen stat.")
            return self._render_kinetic_stat_clip(kinetic_stat or {}, duration)

        # ── Lower-third count-up bar ──────────────────────────────────────────
        bar_h = 140
        lbl_font  = self._load_best_font(fsize=52)
        val_font  = self._load_best_font(fsize=80)

        def make_bar_frame(t):
            progress = min(t / max(duration * 0.80, 0.01), 1.0)
            ease     = 1.0 - (1.0 - progress) ** 3
            current  = int(ease * value) if value is not None else 0

            bar = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(bar)
            # Semi-transparent dark band
            draw.rectangle([(0, 0), (w, bar_h)], fill=(5, 5, 18, 210))
            # Left accent stripe
            draw.rectangle([(0, 0), (8, bar_h)], fill=(245, 195, 50, 255))

            val_str = f"{current:,} {unit}" if value is not None else label
            lbl_str = label.upper()

            draw.text((32, 12),       lbl_str, font=lbl_font, fill=(160, 160, 200, 255))
            draw.text((32, 12 + 52 + 8), val_str, font=val_font,  fill=(245, 195, 50, 255))
            return np.array(bar.convert("RGB"))

        bar_clip = VideoClip(make_bar_frame, duration=duration).set_fps(24)
        bar_clip = bar_clip.set_position((0, h - bar_h))

        return CompositeVideoClip([base_clip, bar_clip], size=self.size)

    def create_daily_summary(self, segments: list, audio_path: str, output_path: str, word_offsets: list, durations: list = None, template_mode: bool = False, branding: dict = None, media_paths: list = None, burn_captions: bool = False, asset_manifest: dict = None):
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
                

                
                bg_clips.append(bg.set_start(cumulative_dur))
                cumulative_dur += seg_duration
        
        elif asset_manifest and asset_manifest.get("scenes"):
            # ── Manifest-driven: routes each scene to correct premium visual type ──────
            scenes       = asset_manifest["scenes"]
            sfx_dir      = "automation/media/sfx"
            if not hasattr(self, "sfx_events"): self.sfx_events = []
            
            # Map global word offsets to each scene sequentially for perfect audio-sync
            scene_timings = match_scenes_to_timestamps(scenes, word_offsets, total_duration)
            
            # Rule-based transition assignment
            transitions = []
            for i in range(len(scenes) - 1):
                curr_type = scenes[i].get("visual_type", "image")
                next_type = scenes[i+1].get("visual_type", "image")
                
                if next_type in ("hook_question", "kinetic_stat"):
                    transitions.append("flash")
                elif (curr_type == "image" and next_type == "ai_video") or (curr_type == "ai_video" and next_type == "image"):
                    transitions.append("fade")
                else:
                    transitions.append("cut")

            for i, scene in enumerate(scenes):
                timing = scene_timings[i]
                start_t = timing["start"]
                end_t = timing["end"]
                dur = timing["duration"]
                
                # Crossfade transition before this scene requires 0.5s overlap
                overlap = 0.0
                if i > 0 and transitions[i-1] == "fade":
                    overlap = 0.5
                    
                clip_start = max(0.0, start_t - overlap)
                clip_duration = dur + overlap
                
                atype = scene.get("asset_type", "none")
                apath = scene.get("asset_path")
                vtype = scene.get("visual_type", "image")
                
                print(f"[VideoLong] Scene {i} visual timing: start={clip_start:.3f}s, dur={clip_duration:.3f}s, type='{vtype}'")
                
                try:
                    if vtype == "typewriter_text" and apath and os.path.exists(apath):
                        words = scene.get("typewriter_words")
                        clip = SceneRenderer.render_typewriter(apath, scene.get("narration", ""), clip_duration, typewriter_words=words)
                    elif vtype == "kinetic_stat" and apath and os.path.exists(apath):
                        sdata = scene.get("stat_data") or {"value": 0, "unit": "", "label": ""}
                        clip = SceneRenderer.render_kinetic_stat(apath, scene.get("narration", ""), clip_duration, sdata)
                    elif vtype == "image" and apath and os.path.exists(apath):
                        clip = SceneRenderer.render_image(apath, scene.get("narration", ""), clip_duration, named_entity=scene.get("named_entity"))
                    elif vtype == "ai_video" and apath and os.path.exists(apath):
                        if apath.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                            clip = SceneRenderer.render_ai_video(apath, clip_duration)
                        else:
                            clip = SceneRenderer.render_image(apath, scene.get("narration", ""), clip_duration)
                    elif vtype == "hook_question" and apath and os.path.exists(apath):
                        qtext = scene.get("question_text") or scene.get("narration", "")
                        emp = scene.get("emphasis_phrase")
                        clip = SceneRenderer.render_hook_question(apath, scene.get("narration", ""), clip_duration, qtext, emphasis_phrase=emp)
                    elif vtype == "data_bars" and apath and os.path.exists(apath):
                        bdata = scene.get("bar_data")
                        clip = SceneRenderer.render_data_bars(apath, scene.get("narration", ""), clip_duration, bdata)
                    else:
                        # Standard Image Ken Burns fallback
                        if apath and os.path.exists(apath):
                            clip = SceneRenderer.render_image(apath, scene.get("narration", ""), clip_duration)
                        else:
                            clip = ColorClip(size=self.size, color=(10, 10, 25), duration=clip_duration)
                            
                    clip = clip.set_start(clip_start).set_position("center")
                    
                    if i > 0 and transitions[i-1] == "fade":
                        clip = clip.crossfadein(0.5)
                        
                    bg_clips.append(clip)
                    
                except Exception as e:
                    print(f"[VideoLong] Scene {i} render error ({vtype}): {e}")
                    bg_clips.append(
                        ColorClip(size=self.size, color=(10, 10, 25), duration=clip_duration)
                        .set_start(clip_start)
                    )
                
                # Apply transition effects & SFX at boundaries
                if i > 0:
                    trans = transitions[i-1]
                    if trans == "flash":
                        flash = ColorClip(size=self.size, color=(255, 255, 255), duration=0.0667)
                        flash = flash.set_start(start_t - 0.0333).set_position("center")
                        bg_clips.append(flash)
                        
                        sfx_path = os.path.join(sfx_dir, "whoosh.mp3")
                        if os.path.exists(sfx_path):
                            self.sfx_events.append({"time": start_t - 0.0333, "file": "whoosh.mp3"})
                    elif trans == "fade":
                        sfx_path = os.path.join(sfx_dir, "dong.mp3")
                        if os.path.exists(sfx_path):
                            self.sfx_events.append({"time": start_t, "file": "dong.mp3"})

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
                            # Ensure image is RGB (fixes broadcast error if grayscale)
                            with Image.open(m_path) as img:
                                if img.mode != "RGB":
                                    img = img.convert("RGB")
                                clip = ImageClip(np.array(img)).set_duration(dur)

                        clip = clip.set_start(start_time)
                        w, h = clip.size
                        target_ratio = self.size[0]/self.size[1]
                        if w/h > target_ratio: clip = clip.resize(height=self.size[1])
                        else: clip = clip.resize(width=self.size[0])
                        clip = clip.set_position('center')
                        
                        if not is_video:
                            # Apply a stronger zoom-in effect - SLOWED DOWN (0.15 -> 0.05)
                            clip = clip.resize(lambda t: 1.0 + 0.05 * (t / dur))
                        
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

        if burn_captions:
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
