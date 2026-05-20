import os
import random
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from moviepy.editor import VideoClip, ImageClip, VideoFileClip

# Size constants will be handled by SceneRenderer instance

def get_font_path(style="bold") -> str:
    """
    Finds and returns the path to a valid font.
    Fallback chain:
    1. Barlow fonts downloaded to automation/fonts/
    2. /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf (guaranteed on Ubuntu 22.04+)
    3. Raise explicit error before rendering.
    """
    mapping = {
        "condensed_bold": "Barlow-CondensedBold.ttf",
        "bold": "Barlow-Bold.ttf",
        "regular": "Barlow-Regular.ttf"
    }
    font_file = mapping.get(style, "Barlow-Bold.ttf")
    local_path = os.path.join("automation", "fonts", font_file)
    if os.path.exists(local_path):
        return local_path
    
    # Fallback to DejaVuSans-Bold
    system_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if os.path.exists(system_path):
        return system_path
        
    # Strict fail-fast mandate (Prevents blank box Devanagari errors)
    raise RuntimeError(
        f"CRITICAL FONT ERROR: Barlow fonts in 'automation/fonts/' and system fallback "
        f"'{system_path}' are BOTH missing! Render aborted."
    )

def wrap_text(text, font, max_width):
    """Wraps text into multiple lines for drawing."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        try:
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
        except AttributeError:
            w = font.getsize(test_line)[0]
            
        if w > max_width:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def apply_cinematic_grade(pil_img):
    """Applies a premium cinematic color grade, vignette, and contrast boost."""
    # Contrast and color saturation boost
    pil_img = ImageEnhance.Contrast(pil_img).enhance(1.18)
    pil_img = ImageEnhance.Color(pil_img).enhance(1.06)
    
    # Create smooth radial vignette using numpy
    w, h = pil_img.size
    x = np.linspace(-1.1, 1.1, w)
    y = np.linspace(-1.1, 1.1, h)
    xx, yy = np.meshgrid(x, y)
    r = np.sqrt(xx**2 + yy**2)
    
    # Smooth roll-off: vignette starts at r=0.45, reaches max opacity 140 at r=1.4
    alpha = np.clip((r - 0.45) / 0.95 * 140, 0, 140).astype(np.uint8)
    
    v_arr = np.zeros((h, w, 4), dtype=np.uint8)
    v_arr[:, :, 3] = alpha
    v_img = Image.fromarray(v_arr, mode="RGBA")
    
    graded = Image.alpha_composite(pil_img.convert("RGBA"), v_img)
    return graded.convert("RGB")

def render_lower_third(draw, named_entity, font_bold, font_regular, width, height, mode='landscape'):
    """Draws a premium banner for named entities (top-left for portrait, bottom-left for landscape)."""
    banner_w = 550
    banner_h = 90
    banner_x = 80
    
    if mode == 'portrait':
        # Top-left placement for portrait (Shorts) to avoid overlaps
        banner_y = 120
    else:
        # Bottom-left placement for landscape (Longform)
        banner_y = height - 180
        
    # Soft black/blue pill background
    pill_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pill_overlay)
    
    # Semi-transparent dark navy pill
    p_draw.rounded_rectangle(
        [(banner_x, banner_y), (banner_x + banner_w, banner_y + banner_h)],
        radius=12,
        fill=(10, 22, 40, 210)
    )
    # Bright cyan left border bar
    p_draw.rectangle(
        [(banner_x, banner_y + 10), (banner_x + 6, banner_y + banner_h - 10)],
        fill=(0, 240, 255, 255)
    )
    
    return pill_overlay, banner_x, banner_y

class SceneRenderer:
    """
    Renders the 6 custom science channel visual scene styles.
    Uses MoviePy 1.x-compatible methods (e.g. set_duration, set_position).
    """
    def __init__(self, mode='landscape'):
        self.mode = mode
        if mode == 'portrait':
            self.WIDTH, self.HEIGHT = 1080, 1920
        else:
            self.WIDTH, self.HEIGHT = 1920, 1080
        self.image_scene_count = 0

    def render_typewriter(self, bg_path: str, text: str, duration: float, typewriter_words: list = None, word_offsets: list = None, start_time: float = 0.0) -> VideoClip:
        """
        Types words sequentially with a blinking cursor at the narration end time.
        Uses a solid dark premium background and kinetic typography (highlighted words are larger/colored).
        """
        font_path_bold = get_font_path("bold")
        font_path_reg = get_font_path("regular")
        
        # Determine display text: use typewriter_words if provided, or cap narration
        max_words = 4 if self.mode == 'portrait' else 8
        if typewriter_words and isinstance(typewriter_words, list):
            processed_words = []
            for w in typewriter_words:
                if isinstance(w, dict):
                    word_str = str(w.get("word", "")).strip()
                    weight = str(w.get("weight", "")).strip().lower()
                    if weight in ("bold", "lg", "large", "highlight"):
                        processed_words.append(f"*{word_str}*")
                    else:
                        processed_words.append(word_str)
                else:
                    processed_words.append(str(w).strip())
            display_text = " ".join(processed_words)
        else:
            words_list = text.split()
            display_text = " ".join(words_list[:max_words])
            if len(words_list) > max_words:
                display_text += "..."

        # Parse highlighted words marked with asterisks
        tokens = []
        in_highlight = False
        for word in display_text.split():
            clean_word = word
            if clean_word.startswith('*'):
                in_highlight = True
                clean_word = clean_word[1:]
            
            was_highlight = in_highlight
            
            if clean_word.endswith('*'):
                clean_word = clean_word[:-1]
                in_highlight = False
                
            tokens.append({"word": clean_word, "highlight": was_highlight})
            
        is_port = self.mode == 'portrait'
        f_bold_sz = int(80 * 1.2) if is_port else 110
        f_reg_sz = int(50 * 1.2) if is_port else 70
        line_spacing = int(105 * 1.2) if is_port else 140
        text_baseline_offset = int(80 * 1.2) if is_port else 110
        
        font_bold = ImageFont.truetype(font_path_bold, f_bold_sz)
        font_reg = ImageFont.truetype(font_path_reg, f_reg_sz)
        
        COLOR_NORMAL = (200, 200, 200)
        # Select a random premium highlight color
        COLOR_HIGHLIGHT = random.choice([(0, 240, 255), (255, 170, 0), (0, 255, 150)])
        
        # Calculate line wrapping
        lines = []
        current_line = []
        current_width = 0
        max_line_width = self.WIDTH - 150 if is_port else self.WIDTH - 300
        
        for token in tokens:
            font = font_bold if token['highlight'] else font_reg
            space_w = font.getlength(" ")
            word_w = font.getlength(token['word'])
            
            item_w = word_w if not current_line else word_w + space_w
            
            if current_width + item_w > max_line_width and current_line:
                lines.append(current_line)
                current_line = [{"word": token['word'], "highlight": token['highlight'], "font": font, "w": word_w}]
                current_width = word_w
            else:
                current_line.append({"word": token['word'], "highlight": token['highlight'], "font": font, "w": word_w, "space_w": space_w if current_line else 0})
                current_width += item_w
        if current_line:
            lines.append(current_line)
            
        total_chars = sum(len(item['word']) for line in lines for item in line)
        
        total_h = len(lines) * line_spacing
        start_y = (self.HEIGHT - total_h) // 2
        
        def make_frame(t):
            # Plane blank page with a sleek premium dark gray color
            img = Image.new("RGB", (self.WIDTH, self.HEIGHT), (15, 18, 22))
            draw = ImageDraw.Draw(img)
            
            typing_duration = min(3.5, duration)
            if word_offsets and start_time is not None:
                scene_words = [item for item in word_offsets if start_time - 0.05 <= item['start'] <= start_time + duration + 0.05]
                if scene_words:
                    words_dur = scene_words[-1]['start'] + scene_words[-1]['duration'] - scene_words[0]['start']
                    words_dur = max(0.5, min(4.5, words_dur))
                    ratio = min(1.0, t / words_dur)
                    visible_chars = int(ratio * total_chars)
                else:
                    visible_chars = int(min(t / max(0.01, typing_duration), 1.0) * total_chars)
            else:
                visible_chars = int(min(t / max(0.01, typing_duration), 1.0) * total_chars)
                
            chars_drawn = 0
            
            y = start_y
            last_x, last_y = 0, 0
            cursor_drawn = False
            
            for line in lines:
                line_width = sum(item['w'] + item.get('space_w', 0) for item in line)
                x = (self.WIDTH - line_width) // 2
                
                for item in line:
                    x += item.get('space_w', 0)
                    word = item['word']
                    font = item['font']
                    color = COLOR_HIGHLIGHT if item['highlight'] else COLOR_NORMAL
                    
                    word_len = len(word)
                    
                    if chars_drawn + word_len <= visible_chars:
                        draw.text((x, y + text_baseline_offset), word, fill=color, font=font, anchor="ls")
                        chars_drawn += word_len
                        x += item['w']
                        last_x, last_y = x, y
                    elif chars_drawn < visible_chars:
                        part_len = visible_chars - chars_drawn
                        part_word = word[:part_len]
                        draw.text((x, y + text_baseline_offset), part_word, fill=color, font=font, anchor="ls")
                        
                        part_w = font.getlength(part_word)
                        cursor_x = x + part_w + 5
                        draw.rectangle([(cursor_x, y + 15), (cursor_x + 6, y + text_baseline_offset + 5)], fill=COLOR_HIGHLIGHT)
                        cursor_drawn = True
                        
                        chars_drawn += word_len
                        x += item['w']
                    else:
                        x += item['w']
                        
                y += line_spacing
                
            if not cursor_drawn and chars_drawn >= total_chars:
                if int(t * 3.5) % 2 == 0:
                    draw.rectangle([(last_x + 8, last_y + 15), (last_x + 14, last_y + text_baseline_offset + 5)], fill=COLOR_HIGHLIGHT)
                    
            return np.array(img)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    def render_kinetic_stat(self, bg_path: str, text: str, duration: float, stat_data: dict) -> VideoClip:
        """
        Renders a large statistical number counting up dynamically.
        """
        font_path_bold = get_font_path("condensed_bold")
        font_path_reg = get_font_path("regular")
        
        bg_img = Image.open(bg_path).convert("RGB").resize((self.WIDTH, self.HEIGHT))
        bg_graded = apply_cinematic_grade(bg_img)
        
        # Parse value: number or string
        val_str = str(stat_data.get("value", "0"))
        unit = str(stat_data.get("unit", ""))
        label = str(stat_data.get("label", "Key Statistic")).upper()
        
        # Try extracting digits for animation
        digits = "".join(c for c in val_str if c.isdigit())
        final_val = int(digits) if digits else 0
        non_digits = "".join(c for c in val_str if not c.isdigit())
        
        def make_frame(t):
            # Counter counts up over first 1.6s using ease-out
            anim_dur = min(1.6, duration)
            if t < anim_dur:
                fraction = 1.0 - (1.0 - t / anim_dur)**3  # ease-out cubic
                cur_val = int(fraction * final_val)
            else:
                cur_val = final_val
                
            display_val = f"{cur_val:,}" + non_digits
            if unit:
                display_val += " " + unit
                
            img = bg_graded.copy()
            
            # Left border accent bar for premium look
            overlay = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 100))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rectangle([(80, 0), (90, self.HEIGHT)], fill=(0, 240, 255, 255))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Huge Stat Value
            stat_font = ImageFont.truetype(font_path_bold, int(180 * (1.2 if self.mode == 'portrait' else 1.0)))
            draw.text((150, self.HEIGHT // 2 - 120), display_val, fill=(0, 240, 255), font=stat_font)
            
            # Label
            label_font = ImageFont.truetype(font_path_reg, int(45 * (1.2 if self.mode == 'portrait' else 1.0)))
            draw.text((155, self.HEIGHT // 2 + 70), label, fill=(255, 255, 255), font=label_font)
            
            # Context narration printed smaller
            narration_font = ImageFont.truetype(font_path_reg, int(32 * (1.2 if self.mode == 'portrait' else 1.0)))
            lines = wrap_text(text, narration_font, self.WIDTH - 300)
            if self.mode == 'portrait':
                ny = self.HEIGHT // 2 + 180  # Center-to-lower region, safe from YT UI overlays
            else:
                ny = self.HEIGHT - 180
            for line in lines:
                draw.text((155, ny), line, fill=(200, 200, 200), font=narration_font)
                ny += int(42 * (1.2 if self.mode == 'portrait' else 1.0))
                
            return np.array(img)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    def render_image(self, bg_path: str, text: str, duration: float, named_entity: str = None) -> VideoClip:
        """
        Applies a Ken Burns zoom/pan, cinematic grades, and adds lower thirds if named_entity exists.
        """
        font_path_bold = get_font_path("bold")
        font_path_reg = get_font_path("regular")
        
        pil_img = Image.open(bg_path).convert("RGB")
        img_w, img_h = pil_img.size
        
        # Setup lower third pill once if present
        lt_overlay = None
        if named_entity:
            # Generate the lower-third text overlay off-screen
            dummy = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(dummy)
            lt_overlay, bx, by = render_lower_third(
                draw, named_entity,
                ImageFont.truetype(font_path_bold, int(36 * (1.2 if self.mode == 'portrait' else 1.0))),
                ImageFont.truetype(font_path_reg, int(24 * (1.2 if self.mode == 'portrait' else 1.0))),
                self.WIDTH, self.HEIGHT,
                self.mode
            )
            # Draw lower-third text inside the pill
            t_draw = ImageDraw.Draw(lt_overlay)
            t_draw.text((bx + 30, by + 15), named_entity.upper(), fill=(0, 240, 255, 255), font=ImageFont.truetype(font_path_bold, int(32 * (1.1 if self.mode == 'portrait' else 1.0))))
            t_draw.text((bx + 30, by + 50), "SCIENTIFIC EVIDENCE", fill=(200, 200, 200, 255), font=ImageFont.truetype(font_path_reg, int(18 * (1.1 if self.mode == 'portrait' else 1.0))))

        self.image_scene_count += 1
        pan_type = self.image_scene_count % 3

        def make_frame(t):
            # Ken Burns effect
            if self.mode == 'portrait':
                scale = 1.0 + 0.15 * (t / duration)
                cw, ch = int(self.WIDTH / scale), int(self.HEIGHT / scale)
                
                if pan_type == 0:
                    # zoom-in-center
                    x_start = (img_w - cw) // 2
                    y_start = (img_h - ch) // 2
                elif pan_type == 1:
                    # zoom-in-top-right
                    x_start = img_w - cw
                    y_start = 0
                else:
                    # pan-left-to-right (no zoom, or slight zoom to allow pan)
                    cw, ch = int(self.WIDTH / 1.15), int(self.HEIGHT / 1.15)
                    max_x = img_w - cw
                    x_start = int(max_x * (t / duration))
                    y_start = (img_h - ch) // 2
            else:
                scale = 1.0 + 0.08 * (t / duration)
                cw, ch = int(self.WIDTH / scale), int(self.HEIGHT / scale)
                x_start = (img_w - cw) // 2
                y_start = (img_h - ch) // 2

            cropped = pil_img.crop((x_start, y_start, x_start + cw, y_start + ch))
            
            resized = cropped.resize((self.WIDTH, self.HEIGHT), Image.Resampling.LANCZOS)
            graded = apply_cinematic_grade(resized)
            
            # Composite named entity pill if present
            if lt_overlay:
                graded_rgba = Image.alpha_composite(graded.convert("RGBA"), lt_overlay)
                return np.array(graded_rgba.convert("RGB"))
                
            return np.array(graded)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    def render_ai_video(self, video_path: str, duration: float) -> VideoClip:
        """
        Loads, scales, and loops the downloaded AI video file, applying cinematic grading.
        """
        vc = VideoFileClip(video_path)
        
        # Loop video to match requested duration
        if vc.duration < duration:
            from moviepy.video.fx.all import loop
            vc = loop(vc, duration=duration)
        else:
            vc = vc.subclip(0, duration)
            
        vc = vc.resize(newsize=(self.WIDTH, self.HEIGHT))
        
        # Apply cinematic grade frame by frame
        def grade_filter(frame):
            pil_frm = Image.fromarray(frame)
            graded = apply_cinematic_grade(pil_frm)
            return np.array(graded)
            
        return vc.fl_image(grade_filter).set_fps(30)

    def render_hook_question(self, bg_path: str, text: str, duration: float, question_text: str, emphasis_phrase: str = None, word_offsets: list = None, start_time: float = 0.0, topic: str = "") -> VideoClip:
        """
        Renders a jaw-dropping premium rhetorical question opening scene.
        Highlights and scales the scientific emphasis phrase, adds glowing underlines,
        and uses snappy typewriter animation (perfect audio sync).
        """
        font_path_bold = get_font_path("bold")
        font_path_reg = get_font_path("regular")
        
        # Heavily blur the background image to make the question pop
        from PIL import ImageFilter
        bg_img = Image.open(bg_path).convert("RGB").resize((self.WIDTH, self.HEIGHT)).filter(ImageFilter.GaussianBlur(15))
        bg_graded = apply_cinematic_grade(bg_img)
        
        raw_text_source = (question_text or text).strip().upper()
        # Clean asterisks from raw source
        raw_text_source = raw_text_source.replace('*', '')
        
        topic_clean = (topic or "").strip().upper()
        is_port = self.mode == 'portrait'
        
        # Font Sizes (Adjusted for high-end cinematic scaling)
        if is_port:
            f_small_sz = 52  # nice and readable
            f_huge_sz = 86   # extremely prominent!
            f_main_sz = int(86 * 1.15) # scaled by 15% for main subject
            f_reg_sz = 68
            line_spacing = 100
        else:
            f_small_sz = 62
            f_huge_sz = 100
            f_main_sz = int(100 * 1.15) # scaled by 15% for main subject
            f_reg_sz = 78
            line_spacing = 120
            
        font_small = ImageFont.truetype(font_path_reg, f_small_sz)
        font_huge = ImageFont.truetype(font_path_bold, f_huge_sz)
        font_main_subj = ImageFont.truetype(font_path_bold, f_main_sz)
        font_reg = ImageFont.truetype(font_path_bold, f_reg_sz)
        
        COLOR_CYAN = (0, 240, 255)
        COLOR_GOLD = (255, 215, 0)
        COLOR_WHITE = (255, 255, 255)
        
        # --- Advanced Semantic Parser ---
        # 1. Hook starters
        starters = [
            "WHAT IF WE TOLD YOU THAT",
            "WHAT IF WE TOLD YOU",
            "CAN YOU REALLY GROW",
            "CAN YOU REALLY",
            "DID YOU KNOW THAT",
            "COULD THIS BE",
            "IS IT POSSIBLE TO",
            "IS IT POSSIBLE",
            "WHAT IF",
            "HOW"
        ]
        
        # Subjects (Gold) - Removed GEOMETRY and SYMMETRY so they match as features (Cyan)
        subjects = [
            "BISMUTH CRYSTALS", "BISMUTH CRYSTAL", "BISMUTH",
            "A CRYSTAL", "CRYSTALS", "CRYSTAL", "PULSARS", "PULSAR",
            "NEBULAS", "NEBULA", "BLACK HOLES", "BLACK HOLE",
            "STARS", "STAR", "SPACE", "LIGHT", "WAVELENGTH"
        ]
        # Features/Action (Cyan)
        features = []
        emp_clean = (emphasis_phrase or "").strip().upper().replace('*', '')
        if emp_clean:
            features.append(emp_clean)
        features.extend([
            "RAINBOW-COLORED APPEARANCE",
            "RAINBOW-COLORED", "RAINBOW COLORED",
            "GEOMETRY AND SYMMETRY", "GEOMETRY", "SYMMETRY",
            "DEFYS THE RULES OF", "DEFIES THE RULES OF", "DEFYS", "DEFIES",
            "SPIN HUNDREDS OF TIMES", "SPIN HUNDREDS", "SPINNING", "SPIN",
            "GLOWING", "GLOW", "SHINING", "SHINE", "UNLIKE ANY OTHER"
        ])
        
        # Enforce exact user request hook matching
        normalized = raw_text_source
        starter_found = ""
        for s in starters:
            if normalized.startswith(s):
                starter_found = s
                break
                
        lines_to_draw = []
        rest = normalized
        if starter_found:
            lines_to_draw.append({"text": starter_found, "type": "small", "font": font_small, "color": COLOR_WHITE})
            rest = normalized[len(starter_found):].strip()
            
        # Parse the rest into subjects and features
        while rest:
            earliest_idx = -1
            best_match = None
            match_type = None
            
            for sub in subjects:
                idx = rest.find(sub)
                if idx != -1 and (earliest_idx == -1 or idx < earliest_idx):
                    earliest_idx = idx
                    best_match = sub
                    match_type = "subject"
                    
            for feat in features:
                idx = rest.find(feat)
                if idx != -1 and (earliest_idx == -1 or idx < earliest_idx):
                    if earliest_idx == idx and best_match and len(feat) > len(best_match):
                        best_match = feat
                        match_type = "feature"
                    elif earliest_idx == -1 or idx < earliest_idx:
                        earliest_idx = idx
                        best_match = feat
                        match_type = "feature"
                        
            if earliest_idx != -1:
                before = rest[:earliest_idx].strip()
                if before:
                    lines_to_draw.append({"text": before, "type": "small", "font": font_small, "color": COLOR_WHITE})
                lines_to_draw.append({"text": best_match, "type": match_type, "font": font_huge, "color": COLOR_GOLD if match_type == "subject" else COLOR_CYAN})
                rest = rest[earliest_idx + len(best_match):].strip()
            else:
                lines_to_draw.append({"text": rest, "type": "small", "font": font_small, "color": COLOR_WHITE})
                rest = ""
                
        # Merge and clean empty/duplicate items
        cleaned = []
        for l in lines_to_draw:
            txt = l["text"].strip()
            if not txt:
                continue
            if cleaned and cleaned[-1]["type"] == "small" and l["type"] == "small":
                cleaned[-1]["text"] += " " + txt
            else:
                cleaned.append({"text": txt, "type": l["type"], "font": l["font"], "color": l["color"]})
                
        # Split long small text lines
        final_lines = []
        for l in cleaned:
            txt = l["text"]
            t_type = l["type"]
            if t_type == "small" and len(txt) > 30:
                words = txt.split()
                cur = []
                for w in words:
                    cur.append(w)
                    if len(" ".join(cur)) > 25:
                        final_lines.append({"text": " ".join(cur), "type": "small", "font": font_small, "color": COLOR_WHITE})
                        cur = []
                if cur:
                    final_lines.append({"text": " ".join(cur), "type": "small", "font": font_small, "color": COLOR_WHITE})
            else:
                # Dynamic visual styles upgrade based on keywords
                txt_upper = txt.upper()
                if t_type == "subject" or "CRYSTAL" in txt_upper or "BISMUTH" in txt_upper:
                    l["font"] = font_main_subj
                    l["type"] = "main_subject"
                    l["color"] = COLOR_GOLD
                elif t_type == "feature" or "GEOMETRY" in txt_upper or "SYMMETRY" in txt_upper or (emp_clean and emp_clean in txt_upper):
                    l["font"] = font_huge
                    l["type"] = "feature"
                    l["color"] = COLOR_CYAN
                final_lines.append(l)
                
        lines_to_draw = final_lines
                
        total_chars = sum(len(line["text"]) for line in lines_to_draw)
        
        # Layout vertical positions
        total_h = 0
        for line in lines_to_draw:
            is_emp = line["type"] in ("subject", "feature", "main_subject")
            if line["type"] == "main_subject":
                fsz = f_main_sz
            elif line["type"] == "feature":
                fsz = f_huge_sz
            else:
                fsz = f_small_sz
            total_h += fsz + (35 if is_emp else 15)
        start_y = (self.HEIGHT - total_h) // 2

        # Snap typing speed to complete in max 3.5s (perfect narrator sync fallback)
        typing_duration = min(3.5, duration)

        def make_frame(t):
            # Create frame as RGBA to allow premium alpha compositing/neon glow
            img = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Full screen soft transparent dark overlay instead of restrictive box
            draw.rectangle(
                [(0, 0), (self.WIDTH, self.HEIGHT)],
                fill=(10, 15, 30, 180)
            )
            
            # Word sync / typewriter character limit
            if word_offsets and start_time is not None:
                scene_words = [item for item in word_offsets if start_time - 0.05 <= item['start'] <= start_time + duration + 0.05]
                if scene_words:
                    words_dur = scene_words[-1]['start'] + scene_words[-1]['duration'] - scene_words[0]['start']
                    words_dur = max(0.5, min(4.5, words_dur))
                    ratio = min(1.0, t / words_dur)
                    visible_chars = int(ratio * total_chars)
                else:
                    visible_chars = int(min(t / max(0.01, min(3.5, duration)), 1.0) * total_chars)
            else:
                visible_chars = int(min(t / max(0.01, min(3.5, duration)), 1.0) * total_chars)
                
            chars_drawn = 0
            
            y_start = start_y
            last_x, last_y, last_font_sz = 0, 0, f_small_sz
            cursor_drawn = False
            
            for line in lines_to_draw:
                txt = line["text"]
                font = line["font"]
                color = line["color"]
                l_type = line["type"]
                is_emp = l_type in ("subject", "feature", "topic", "emphasis", "main_subject")
                if l_type == "main_subject":
                    font_sz = f_main_sz
                elif is_emp:
                    font_sz = f_huge_sz
                else:
                    font_sz = f_small_sz
                
                # Center line width calculation
                try:
                    line_w = font.getbbox(txt)[2] - font.getbbox(txt)[0]
                except AttributeError:
                    line_w = draw.textlength(txt, font=font)
                    
                x = (self.WIDTH - line_w) // 2
                line_len = len(txt)
                
                if chars_drawn + line_len <= visible_chars:
                    # Line completely typed
                    if is_emp:
                        # Draw soft neon vector glow layers behind the emphasized word
                        for r in range(1, 6):
                            opacity = int(55 / r)
                            draw.text(
                                (x, y_start), txt,
                                fill=(color[0], color[1], color[2], opacity),
                                font=font, stroke_width=r
                            )
                        # Sharp main text
                        draw.text((x, y_start), txt, fill=color, font=font)
                        
                        # Glowing premium underline
                        line_y_base = y_start + font_sz + 8
                        for r in range(1, 4):
                            op = int(60 / r)
                            draw.line([(x, line_y_base), (x + line_w, line_y_base)], fill=(color[0], color[1], color[2], op), width=r * 2)
                        draw.line([(x, line_y_base), (x + line_w, line_y_base)], fill=(255, 255, 255, 255), width=2)
                    else:
                        draw.text((x, y_start), txt, fill=color, font=font)
                        
                    chars_drawn += line_len
                    last_x, last_y, last_font_sz = x + line_w, y_start, font_sz
                elif chars_drawn < visible_chars:
                    # Line partially typed
                    part_len = visible_chars - chars_drawn
                    part_txt = txt[:part_len]
                    
                    try:
                        part_w = font.getbbox(part_txt)[2] - font.getbbox(part_txt)[0]
                    except AttributeError:
                        part_w = draw.textlength(part_txt, font=font)
                        
                    if is_emp:
                        # Draw soft neon glow behind partial text
                        for r in range(1, 6):
                            opacity = int(55 / r)
                            draw.text(
                                (x, y_start), part_txt,
                                fill=(color[0], color[1], color[2], opacity),
                                font=font, stroke_width=r
                            )
                        draw.text((x, y_start), part_txt, fill=color, font=font)
                        
                        # Draw partial underline to follow typing!
                        line_y_base = y_start + font_sz + 8
                        draw.line([(x, line_y_base), (x + part_w, line_y_base)], fill=color, width=3)
                    else:
                        draw.text((x, y_start), part_txt, fill=color, font=font)
                        
                    cursor_x = x + part_w + 4
                    # Blinking cursor block
                    draw.rectangle(
                        [(cursor_x, y_start + 8), (cursor_x + 8, y_start + font_sz - 4)],
                        fill=COLOR_GOLD
                    )
                    cursor_drawn = True
                    chars_drawn += line_len
                    last_x, last_y, last_font_sz = cursor_x, y_start, font_sz
                    break
                else:
                    break
                
                y_start += font_sz + (35 if is_emp else 15)
                
            # Keep cursor blinking at the end of text
            if not cursor_drawn and chars_drawn >= total_chars:
                if int(t * 3.5) % 2 == 0:
                    draw.rectangle(
                        [(last_x + 8, last_y + 8), (last_x + 16, last_y + last_font_sz - 4)],
                        fill=COLOR_GOLD
                    )
                    
            # Overlay composite onto cinematic blurred background
            final_img = bg_graded.copy().convert("RGBA")
            final_img = Image.alpha_composite(final_img, img)
            return np.array(final_img.convert("RGB"))

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    def render_data_bars(self, bg_path: str, text: str, duration: float, bar_data: list) -> VideoClip:
        """
        Compares multiple values using animated 3D-styled data bars.
        """
        font_path_bold = get_font_path("condensed_bold")
        font_path_reg = get_font_path("regular")
        
        bg_img = Image.open(bg_path).convert("RGB").resize((self.WIDTH, self.HEIGHT))
        bg_graded = apply_cinematic_grade(bg_img)
        
        if not bar_data or not isinstance(bar_data, list):
            # Fallback bar data
            bar_data = [
                {"label": "Value A", "value": 30},
                {"label": "Value B", "value": 75},
                {"label": "Value C", "value": 50}
            ]
            
        values = [float(b.get("value", 0)) for b in bar_data]
        max_val = max(values) if max(values) > 0 else 1.0
        
        # Design Dimensions
        is_port = self.mode == 'portrait'
        bar_count = len(bar_data)
        chart_w = (self.WIDTH - 160) if is_port else 1200
        chart_h = (self.HEIGHT // 3) if is_port else 500
        chart_x = (self.WIDTH - chart_w) // 2
        chart_y = (self.HEIGHT - chart_h) // 2
        
        bar_gap = 30 if is_port else 60
        total_gaps_w = bar_gap * (bar_count - 1)
        bar_w = (chart_w - total_gaps_w) // bar_count
        
        def make_frame(t):
            img = bg_graded.copy()
            
            # Semi-transparent backing panel
            overlay = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rounded_rectangle(
                [(chart_x - (20 if is_port else 60), chart_y - (60 if is_port else 80)), (chart_x + chart_w + (20 if is_port else 60), chart_y + chart_h + (80 if is_port else 100))],
                radius=16,
                fill=(10, 22, 40, 220)
            )
            # Accent divider bar
            o_draw.rectangle(
                [(chart_x, chart_y + chart_h), (chart_x + chart_w, chart_y + chart_h + 4)],
                fill=(0, 240, 255, 255)
            )
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Title
            title_font = ImageFont.truetype(font_path_bold, 30 if is_port else 40)
            draw.text((chart_x, chart_y - (45 if is_port else 50)), "COMPARATIVE SCIENTIFIC ANALYSIS", fill=(0, 240, 255), font=title_font)
            
            # Bar growth animation: ease-out over first 1.3 seconds
            anim_dur = min(1.3, duration)
            fraction = 1.0 if t >= anim_dur else 1.0 - (1.0 - t / anim_dur)**3
            
            label_font = ImageFont.truetype(font_path_reg, 18 if is_port else 24)
            val_font = ImageFont.truetype(font_path_bold, 20 if is_port else 30)
            
            for i, item in enumerate(bar_data):
                lbl = str(item.get("label", "")).upper()
                val = float(item.get("value", 0))
                
                # Height calculation
                pct = val / max_val
                target_bar_h = int(pct * chart_h)
                current_bar_h = int(target_bar_h * fraction)
                
                bx1 = chart_x + i * (bar_w + bar_gap)
                by1 = chart_y + chart_h - current_bar_h
                bx2 = bx1 + bar_w
                by2 = chart_y + chart_h
                
                # Render bar with dynamic color gradient
                # Choose color based on index (Cyber Cyan, Cyber Magenta, Purple, Orange)
                colors = [
                    (0, 240, 255),  # Cyan
                    (255, 0, 180),  # Magenta
                    (150, 0, 255),  # Purple
                    (255, 120, 0)   # Orange
                ]
                bar_color = colors[i % len(colors)]
                
                # Draw the main bar body
                draw.rectangle([(bx1, by1), (bx2, by2)], fill=bar_color)
                # 3D side highlight edge
                edge_w = 4 if is_port else 8
                draw.rectangle([(bx2 - edge_w, by1), (bx2, by2)], fill=(max(0, bar_color[0] - 50), max(0, bar_color[1] - 50), max(0, bar_color[2] - 50)))
                
                # Render numeric value above bar
                if current_bar_h > 20 or t >= anim_dur:
                    val_text = f"{val:g}"
                    try:
                        vw = val_font.getbbox(val_text)[2] - val_font.getbbox(val_text)[0]
                    except AttributeError:
                        vw = val_font.getsize(val_text)[0]
                    vx = bx1 + (bar_w - vw) // 2
                    draw.text((vx, by1 - (30 if is_port else 40)), val_text, fill=(255, 255, 255), font=val_font)
                
                # Render label below chart axis
                try:
                    lw = label_font.getbbox(lbl)[2] - label_font.getbbox(lbl)[0]
                except AttributeError:
                    lw = label_font.getsize(lbl)[0]
                lx = bx1 + (bar_w - lw) // 2
                draw.text((lx, by2 + (12 if is_port else 20)), lbl, fill=(200, 200, 200), font=label_font)
                
            return np.array(img)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)
