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
        
        # Parse highlighted words marked with asterisks
        tokens = []
        in_highlight = False
        for word in text.split():
            clean_word = word
            if clean_word.startswith('*'):
                in_highlight = True
                clean_word = clean_word[1:]
            
            was_highlight = in_highlight
            
            if clean_word.endswith('*'):
                clean_word = clean_word[:-1]
                in_highlight = False
                
            tokens.append({"word": clean_word, "highlight": was_highlight})
            
        font_bold = ImageFont.truetype(font_path_bold, 110)
        font_reg = ImageFont.truetype(font_path_reg, 70)
        
        COLOR_NORMAL = (200, 200, 200)
        # Select a random premium highlight color
        COLOR_HIGHLIGHT = random.choice([(0, 240, 255), (255, 170, 0), (0, 255, 150)])
        
        # Calculate line wrapping
        lines = []
        current_line = []
        current_width = 0
        max_line_width = WIDTH - 300
        
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
        
        total_h = len(lines) * 140
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
                        draw.text((x, y + 110), word, fill=color, font=font, anchor="ls")
                        chars_drawn += word_len
                        x += item['w']
                        last_x, last_y = x, y
                    elif chars_drawn < visible_chars:
                        part_len = visible_chars - chars_drawn
                        part_word = word[:part_len]
                        draw.text((x, y + 110), part_word, fill=color, font=font, anchor="ls")
                        
                        part_w = font.getlength(part_word)
                        cursor_x = x + part_w + 5
                        draw.rectangle([(cursor_x, y + 15), (cursor_x + 6, y + 115)], fill=COLOR_HIGHLIGHT)
                        cursor_drawn = True
                        
                        chars_drawn += word_len
                        x += item['w']
                    else:
                        x += item['w']
                        
                y += 140
                
            if not cursor_drawn and chars_drawn >= total_chars:
                if int(t * 3.5) % 2 == 0:
                    draw.rectangle([(last_x + 8, last_y + 15), (last_x + 14, last_y + 115)], fill=COLOR_HIGHLIGHT)
                    
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
        """
        font_path_bold = get_font_path("condensed_bold")
        font_path_reg = get_font_path("regular")
        
        # Heavily blur the background image to make the question pop
        from PIL import ImageFilter
        bg_img = Image.open(bg_path).convert("RGB").resize((WIDTH, HEIGHT)).filter(ImageFilter.GaussianBlur(15))
        bg_graded = apply_cinematic_grade(bg_img)
        
        q_text = (question_text or text).strip().upper()
        emp_phrase = (emphasis_phrase or "").strip().upper()
        
        def make_frame(t):
            img = bg_graded.copy()
            
            # Transparent overlay box
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 140))
            o_draw = ImageDraw.Draw(overlay)
            
            # Premium double border box in the center
            o_draw.rectangle([(100, 100), (WIDTH - 100, HEIGHT - 100)], outline=(0, 240, 255, 120), width=4)
            o_draw.rectangle([(112, 112), (WIDTH - 112, HEIGHT - 112)], outline=(255, 255, 255, 40), width=1)
            
            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
            draw = ImageDraw.Draw(img)
            
            # Render Hook Question Text
            font_size = 72
            font = ImageFont.truetype(font_path_bold, font_size)
            lines = wrap_text(q_text, font, WIDTH - 350)
            
            total_h = len(lines) * (font_size + 20)
            y_start = (HEIGHT - total_h) // 2
            
            for line in lines:
                try:
                    w = font.getbbox(line)[2] - font.getbbox(line)[0]
                except AttributeError:
                    w = font.getsize(line)[0]
                x = (WIDTH - w) // 2
                
                # If line contains the emphasis phrase, highlight it in amber (#FFB300)
                if emp_phrase and emp_phrase in line:
                    parts = line.split(emp_phrase)
                    # We can draw standard white for prefix/suffix, amber for emphasis
                    pre_w = 0
                    if parts[0]:
                        try:
                            pre_w = font.getbbox(parts[0])[2] - font.getbbox(parts[0])[0]
                        except AttributeError:
                            pre_w = font.getsize(parts[0])[0]
                        draw.text((x, y_start), parts[0], fill=(255, 255, 255), font=font)
                        
                    draw.text((x + pre_w, y_start), emp_phrase, fill=(255, 179, 0), font=font)
                    
                    if len(parts) > 1 and parts[1]:
                        try:
                            emp_w = font.getbbox(emp_phrase)[2] - font.getbbox(emp_phrase)[0]
                        except AttributeError:
                            emp_w = font.getsize(emp_phrase)[0]
                        draw.text((x + pre_w + emp_w, y_start), parts[1], fill=(255, 255, 255), font=font)
                else:
                    draw.text((x, y_start), line, fill=(255, 255, 255), font=font)
                    
                y_start += font_size + 20
                
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
        bar_count = len(bar_data)
        chart_w = 1200
        chart_h = 500
        chart_x = (WIDTH - chart_w) // 2
        chart_y = (HEIGHT - chart_h) // 2
        
        bar_gap = 60
        total_gaps_w = bar_gap * (bar_count - 1)
        bar_w = (chart_w - total_gaps_w) // bar_count
        
        def make_frame(t):
            img = bg_graded.copy()
            
            # Semi-transparent backing panel
            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            o_draw = ImageDraw.Draw(overlay)
            o_draw.rounded_rectangle(
                [(chart_x - 60, chart_y - 80), (chart_x + chart_w + 60, chart_y + chart_h + 100)],
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
            title_font = ImageFont.truetype(font_path_bold, 40)
            draw.text((chart_x, chart_y - 50), "COMPARATIVE SCIENTIFIC ANALYSIS", fill=(0, 240, 255), font=title_font)
            
            # Bar growth animation: ease-out over first 1.3 seconds
            anim_dur = min(1.3, duration)
            fraction = 1.0 if t >= anim_dur else 1.0 - (1.0 - t / anim_dur)**3
            
            label_font = ImageFont.truetype(font_path_reg, 24)
            val_font = ImageFont.truetype(font_path_bold, 30)
            
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
                draw.rectangle([(bx2 - 8, by1), (bx2, by2)], fill=(max(0, bar_color[0] - 50), max(0, bar_color[1] - 50), max(0, bar_color[2] - 50)))
                
                # Render numeric value above bar
                if current_bar_h > 20 or t >= anim_dur:
                    val_text = f"{val:g}"
                    try:
                        vw = val_font.getbbox(val_text)[2] - val_font.getbbox(val_text)[0]
                    except AttributeError:
                        vw = val_font.getsize(val_text)[0]
                    vx = bx1 + (bar_w - vw) // 2
                    draw.text((vx, by1 - 40), val_text, fill=(255, 255, 255), font=val_font)
                
                # Render label below chart axis
                try:
                    lw = label_font.getbbox(lbl)[2] - label_font.getbbox(lbl)[0]
                except AttributeError:
                    lw = label_font.getsize(lbl)[0]
                lx = bx1 + (bar_w - lw) // 2
                draw.text((lx, by2 + 20), lbl, fill=(200, 200, 200), font=label_font)
                
            return np.array(img)

        clip = VideoClip(make_frame, duration=duration)
        return clip.set_fps(30)
