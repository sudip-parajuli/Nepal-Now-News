import os
import random
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from moviepy.editor import VideoClip, ImageClip, VideoFileClip

# Size constants for Daily horizontal videos
WIDTH, HEIGHT = 1920, 1080

def get_font_path(font_style="bold"):
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
    font_file = mapping.get(font_style, "Barlow-Bold.ttf")
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

def render_lower_third(draw, named_entity, font_bold, font_regular):
    """Draws a premium lower-third banner for named entities."""
    # Render soft deep blue banner on bottom left
    banner_w = 550
    banner_h = 90
    banner_x = 80
    banner_y = HEIGHT - 180
    
    # Soft black/blue pill background
    pill_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
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
    
    # Composite the pill overlay
    return pill_overlay

class SceneRenderer:
    """
    Renders the 6 custom science channel visual scene styles.
    Uses MoviePy 1.x-compatible methods (e.g. set_duration, set_position).
    """

    @staticmethod
    def render_typewriter(bg_path: str, text: str, duration: float, typewriter_words: list = None) -> VideoClip:
        """
        Types words sequentially with a blinking cursor at the narration end time.
        Uses a solid dark premium background and kinetic typography (highlighted words are larger/colored).
        """
        font_path_bold = get_font_path("bold")
        font_path_reg = get_font_path("regular")
        
        # Determine display text: use typewriter_words if provided, or cap narration to first 8 words
        if typewriter_words and isinstance(typewriter_words, list):
            display_text = " ".join(str(w) for w in typewriter_words)
        else:
            words_list = text.split()
            display_text = " ".join(words_list[:8])
            if len(words_list) > 8:
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
            
        is_port = WIDTH < 1200
        f_bold_sz = 80 if is_port else 110
        f_reg_sz = 50 if is_port else 70
        line_spacing = 105 if is_port else 140
        text_baseline_offset = 80 if is_port else 110
        
        font_bold = ImageFont.truetype(font_path_bold, f_bold_sz)
        font_reg = ImageFont.truetype(font_path_reg, f_reg_sz)
        
        COLOR_NORMAL = (200, 200, 200)
        # Select a random premium highlight color
        COLOR_HIGHLIGHT = random.choice([(0, 240, 255), (255, 170, 0), (0, 255, 150)])
        
        # Calculate line wrapping
        lines = []
        current_line = []
        current_width = 0
        max_line_width = WIDTH - 200 if is_port else WIDTH - 300
        
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
        start_y = (HEIGHT - total_h) // 2
        
        def make_frame(t):
            # Plane blank page with a sleek premium dark gray color
            img = Image.new("RGB", (WIDTH, HEIGHT), (15, 18, 22))
            draw = ImageDraw.Draw(img)
            
            visible_chars = int((t / max(0.1, duration * 0.85)) * total_chars)
            chars_drawn = 0
            
            y = start_y
            last_x, last_y = 0, 0
            cursor_drawn = False
            
            for line in lines:
                line_width = sum(item['w'] + item.get('space_w', 0) for item in line)
                x = (WIDTH - line_width) // 2
                
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

    @staticmethod
    def render_kinetic_stat(bg_path: str, text: str, duration: float, stat_data: dict) -> VideoClip:
        """
        Renders a large statistical number counting up dynamically.
        """
        font_path_bold = get_font_path("condensed_bold")
        font_path_reg = get_font_path("regular")
        
        bg_img = Image.open(bg_path).convert("RGB").resize((WIDTH, HEIGHT))
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
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 100))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rectangle([(80, 0), (90, HEIGHT)], fill=(0, 240, 255, 255))
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Huge Stat Value
            stat_font = ImageFont.truetype(font_path_bold, 180)
            draw.text((150, HEIGHT // 2 - 120), display_val, fill=(0, 240, 255), font=stat_font)
            
            # Label
            label_font = ImageFont.truetype(font_path_reg, 45)
            draw.text((155, HEIGHT // 2 + 70), label, fill=(255, 255, 255), font=label_font)
            
            # Context narration printed smaller on bottom
            narration_font = ImageFont.truetype(font_path_reg, 32)
            lines = wrap_text(text, narration_font, WIDTH - 300)
            ny = HEIGHT - 180
            for line in lines:
                draw.text((155, ny), line, fill=(200, 200, 200), font=narration_font)
                ny += 42
                
            return np.array(img)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    @staticmethod
    def render_image(bg_path: str, text: str, duration: float, named_entity: str = None) -> VideoClip:
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
            dummy = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(dummy)
            lt_overlay = render_lower_third(
                draw, named_entity,
                ImageFont.truetype(font_path_bold, 36),
                ImageFont.truetype(font_path_reg, 24)
            )
            # Draw lower-third text inside the pill
            t_draw = ImageDraw.Draw(lt_overlay)
            t_draw.text((110, HEIGHT - 165), named_entity.upper(), fill=(0, 240, 255, 255), font=ImageFont.truetype(font_path_bold, 34))
            t_draw.text((110, HEIGHT - 125), "SCIENTIFIC EVIDENCE", fill=(200, 200, 200, 255), font=ImageFont.truetype(font_path_reg, 20))

        def make_frame(t):
            # Ken Burns: Scale from 1.0 to 1.08 slowly
            scale = 1.0 + 0.08 * (t / duration)
            cw, ch = int(WIDTH / scale), int(HEIGHT / scale)
            
            # Determine crop box centered on image
            x_start = (img_w - cw) // 2
            y_start = (img_h - ch) // 2
            cropped = pil_img.crop((x_start, y_start, x_start + cw, y_start + ch))
            
            resized = cropped.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            graded = apply_cinematic_grade(resized)
            
            # Composite named entity pill if present
            if lt_overlay:
                graded_rgba = Image.alpha_composite(graded.convert("RGBA"), lt_overlay)
                return np.array(graded_rgba.convert("RGB"))
                
            return np.array(graded)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    @staticmethod
    def render_ai_video(video_path: str, duration: float) -> VideoClip:
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
            
        vc = vc.resize(newsize=(WIDTH, HEIGHT))
        
        # Apply cinematic grade frame by frame
        def grade_filter(frame):
            pil_frm = Image.fromarray(frame)
            graded = apply_cinematic_grade(pil_frm)
            return np.array(graded)
            
        return vc.fl_image(grade_filter).set_fps(30)

    @staticmethod
    def render_hook_question(bg_path: str, text: str, duration: float, question_text: str, emphasis_phrase: str = None) -> VideoClip:
        """
        Renders an intimidating chapter opening rhetorical question with amber highlights.
        Animates character by character as a typewriter effect.
        """
        font_path_bold = get_font_path("condensed_bold")
        font_path_reg = get_font_path("regular")
        
        # Heavily blur the background image to make the question pop
        from PIL import ImageFilter
        bg_img = Image.open(bg_path).convert("RGB").resize((WIDTH, HEIGHT)).filter(ImageFilter.GaussianBlur(15))
        bg_graded = apply_cinematic_grade(bg_img)
        
        q_text = (question_text or text).strip().upper()
        emp_phrase = (emphasis_phrase or "").strip().upper()
        
        is_port = WIDTH < 1200
        font_size = 52 if is_port else 72
        font = ImageFont.truetype(font_path_bold, font_size)
        lines = wrap_text(q_text, font, WIDTH - 180 if is_port else WIDTH - 350)
        total_chars = sum(len(line) for line in lines)
        total_h = len(lines) * (font_size + 20)
        start_y = (HEIGHT - total_h) // 2

        def make_frame(t):
            img = bg_graded.copy()
            
            # Transparent overlay box
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 140))
            o_draw = ImageDraw.Draw(overlay)
            
            # Premium double border box in the center
            border_pad = 50 if is_port else 100
            o_draw.rectangle([(border_pad, border_pad), (WIDTH - border_pad, HEIGHT - border_pad)], outline=(0, 240, 255, 120), width=4)
            o_draw.rectangle([(border_pad + 12, border_pad + 12), (WIDTH - (border_pad + 12), HEIGHT - (border_pad + 12))], outline=(255, 255, 255, 40), width=1)
            
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Calculate how many characters are currently visible
            visible_chars = int((t / max(0.01, duration * 0.80)) * total_chars)
            chars_drawn = 0
            
            y_start = start_y
            last_x, last_y = 0, 0
            cursor_drawn = False
            
            for line in lines:
                try:
                    w = font.getbbox(line)[2] - font.getbbox(line)[0]
                except AttributeError:
                    w = font.getsize(line)[0]
                x = (WIDTH - w) // 2
                
                # Check how many characters we can draw for this line
                line_len = len(line)
                
                # Segment the line into parts for emphasis highlighting
                segments = []
                if emp_phrase and emp_phrase in line:
                    parts = line.split(emp_phrase)
                    if parts[0]:
                        segments.append({"text": parts[0], "color": (255, 255, 255)})
                    segments.append({"text": emp_phrase, "color": (255, 179, 0)})
                    if len(parts) > 1 and parts[1]:
                        segments.append({"text": parts[1], "color": (255, 255, 255)})
                else:
                    segments.append({"text": line, "color": (255, 255, 255)})
                
                curr_x = x
                for seg in segments:
                    seg_len = len(seg["text"])
                    if chars_drawn + seg_len <= visible_chars:
                        # Draw full segment
                        draw.text((curr_x, y_start), seg["text"], fill=seg["color"], font=font)
                        try:
                            seg_w = font.getbbox(seg["text"])[2] - font.getbbox(seg["text"])[0]
                        except AttributeError:
                            seg_w = font.getsize(seg["text"])[0]
                        curr_x += seg_w
                        chars_drawn += seg_len
                        last_x, last_y = curr_x, y_start
                    elif chars_drawn < visible_chars:
                        # Draw partial segment
                        part_len = visible_chars - chars_drawn
                        part_txt = seg["text"][:part_len]
                        draw.text((curr_x, y_start), part_txt, fill=seg["color"], font=font)
                        try:
                            part_w = font.getbbox(part_txt)[2] - font.getbbox(part_txt)[0]
                        except AttributeError:
                            part_w = font.getsize(part_txt)[0]
                        cursor_x = curr_x + part_w + 5
                        draw.rectangle([(cursor_x, y_start + 10), (cursor_x + 6, y_start + font_size - 10)], fill=(255, 179, 0))
                        cursor_drawn = True
                        chars_drawn += seg_len
                        curr_x += part_w
                        last_x, last_y = cursor_x, y_start
                        break
                    else:
                        break
                
                y_start += font_size + 20
                
            if not cursor_drawn and chars_drawn >= total_chars:
                if int(t * 3.5) % 2 == 0:
                    draw.rectangle([(last_x + 8, last_y + 10), (last_x + 14, last_y + font_size - 10)], fill=(255, 179, 0))
                    
            return np.array(img)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)

    @staticmethod
    def render_data_bars(bg_path: str, text: str, duration: float, bar_data: list) -> VideoClip:
        """
        Compares multiple values using animated 3D-styled data bars.
        """
        font_path_bold = get_font_path("condensed_bold")
        font_path_reg = get_font_path("regular")
        
        bg_img = Image.open(bg_path).convert("RGB").resize((WIDTH, HEIGHT))
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
        is_port = WIDTH < 1200
        bar_count = len(bar_data)
        chart_w = (WIDTH - 160) if is_port else 1200
        chart_h = (HEIGHT // 3) if is_port else 500
        chart_x = (WIDTH - chart_w) // 2
        chart_y = (HEIGHT - chart_h) // 2
        
        bar_gap = 30 if is_port else 60
        total_gaps_w = bar_gap * (bar_count - 1)
        bar_w = (chart_w - total_gaps_w) // bar_count
        
        def make_frame(t):
            img = bg_graded.copy()
            
            # Semi-transparent backing panel
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
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
