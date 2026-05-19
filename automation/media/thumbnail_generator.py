import os
import requests
import random
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np

class ThumbnailGenerator:
    def __init__(self, size=(1280, 720)):
        self.size = size
        self.output_dir = "automation/storage/thumbnails"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_thumbnail(self, info: dict, output_path: str = None) -> str:
        """
        Generates a thumbnail image, routing to the premium science design if data is present.
        """
        if 'thumbnail_data' in info or 'hook_phrase' in info:
            return self.generate_science_thumbnail(info, output_path)
            
        text = info.get('text', 'Amazing Science').upper()
        image_prompt = info.get('image_prompt', 'cinematic science background')
        
        if not output_path:
            clean_text = re.sub(r'[^a-zA-Z0-9]', '_', text)[:20]
            output_path = os.path.join(self.output_dir, f"thumb_{clean_text}.jpg")

        # 1. Generate/Fetch Background
        bg_path = self._fetch_ai_background(image_prompt)
        if not bg_path:
            img = Image.new('RGB', self.size, color=(15, 25, 45))
        else:
            img = Image.open(bg_path).resize(self.size, Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(img)
        font = self._load_font(fsize=120)
        self._draw_dynamic_text(draw, text, font)

        img.save(output_path, "JPEG", quality=90)
        print(f"Thumbnail saved at: {output_path}")
        return output_path

    def _search_image_url(self, query: str) -> str:
        """Searches DuckDuckGo and returns the first valid image URL."""
        from duckduckgo_search import DDGS
        import time
        q = query[:60]
        forbidden = ["cartoon", "illustration", "vector", "drawing", "logo", "diagram"]
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    results = ddgs.images(
                        keywords=q,
                        region="wt-wt",
                        safesearch="on",
                        size="large"
                    )
                    if results:
                        for r in results:
                            url = r.get("image", "")
                            if not url:
                                continue
                            if any(f in url.lower() for f in forbidden):
                                continue
                            return url
            except Exception as e:
                print(f"DDG Search error in ThumbnailGenerator for '{query}': {e}")
                time.sleep(1)
        return None

    def _download_url(self, url: str, filename: str) -> str:
        """Downloads an image from a URL and saves it to storage."""
        save_path = os.path.join(self.output_dir, filename)
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(resp.content)
                return save_path
        except Exception as e:
            print(f"Error downloading {url}: {e}")
        return None

    def generate_science_thumbnail(self, info: dict, output_path: str = None) -> str:
        """
        Generates a premium science channel YouTube thumbnail.
        """
        tdata = info.get('thumbnail_data', {})
        if not tdata:
            tdata = info
            
        hook_phrase = str(tdata.get('hook_phrase', 'AMAZING DISCOVERY')).upper()
        supporting_fact = str(tdata.get('supporting_fact', 'Scientists have uncovered a groundbreaking mystery.'))
        bg_query = str(tdata.get('thumbnail_bg_query', 'cinematic cosmic science background'))
        subject_query = str(tdata.get('thumbnail_subject_query', 'bismuth crystal structure closeup'))
        
        if not output_path:
            clean_text = re.sub(r'[^a-zA-Z0-9]', '_', hook_phrase)[:20]
            output_path = os.path.join(self.output_dir, f"thumb_{clean_text}.jpg")
            
        print(f"[Thumbnail] Generating premium science thumbnail. Hook: '{hook_phrase}'")
        
        # 1. Fetch Background Image via DDG
        bg_url = self._search_image_url(bg_query)
        bg_file = None
        if bg_url:
            bg_file = self._download_url(bg_url, "temp_thumb_bg.jpg")
            
        if bg_file and os.path.exists(bg_file):
            canvas = Image.open(bg_file).resize(self.size, Image.Resampling.LANCZOS)
        else:
            print("[Thumbnail] Background search failed, using Pollinations.ai fallback.")
            fallback_bg = self._fetch_ai_background(bg_query)
            if fallback_bg and os.path.exists(fallback_bg):
                canvas = Image.open(fallback_bg).resize(self.size, Image.Resampling.LANCZOS)
            else:
                canvas = Image.new('RGB', self.size, color=(10, 18, 30))
                
        # 2. Fetch Subject Image via DDG
        sub_url = self._search_image_url(subject_query)
        sub_file = None
        if sub_url:
            sub_file = self._download_url(sub_url, "temp_thumb_subject.jpg")
            
        if sub_file and os.path.exists(sub_file):
            try:
                sub_img = Image.open(sub_file)
                sub_size = (550, 550)
                sub_img = sub_img.resize(sub_size, Image.Resampling.LANCZOS)
                
                # Create radial gradient alpha mask using numpy
                sw, sh = sub_size
                x = np.linspace(-1, 1, sw)
                y = np.linspace(-1, 1, sh)
                xx, yy = np.meshgrid(x, y)
                r = np.sqrt(xx**2 + yy**2)
                
                mask = np.zeros((sh, sw), dtype=np.uint8)
                mask[r <= 0.6] = 255
                fade_mask = (r > 0.6) & (r <= 1.0)
                mask[fade_mask] = (255 * (1.0 - (r[fade_mask] - 0.6) / 0.4)).astype(np.uint8)
                mask[r > 1.0] = 0
                
                mask_img = Image.fromarray(mask, mode="L")
                
                # Apply mask to alpha channel
                sub_rgba = sub_img.convert("RGBA")
                sub_rgba.putalpha(mask_img)
                
                # Paste floating subject onto right side of canvas
                canvas_rgba = canvas.convert("RGBA")
                paste_x = 1280 - 580
                paste_y = (720 - 550) // 2
                canvas_rgba.paste(sub_rgba, (paste_x, paste_y), sub_rgba)
                canvas = canvas_rgba.convert("RGB")
                print("[Thumbnail] Successfully composited floating subject image with radial gradient mask.")
            except Exception as e:
                print(f"[Thumbnail] Subject composting failed: {e}")
                
        # 3. Draw Dark left-third gradient overlay
        overlay = Image.new("RGBA", self.size, (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(overlay)
        for x_coord in range(600):
            alpha = int(230 * (1.0 - x_coord / 600.0))
            o_draw.line([(x_coord, 0), (x_coord, 720)], fill=(5, 11, 20, alpha))
            
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        
        # 4. Draw Left-Side Cyber Cyan Vertical Accent Bar
        accent_x = 55
        accent_y1 = 150
        accent_y2 = 480
        draw.rectangle([(accent_x, accent_y1), (accent_x + 8, accent_y2)], fill=(0, 240, 255))
        
        # 5. Draw Hook Phrase Text (large, bold, left-aligned)
        font_path = "automation/fonts/Barlow-CondensedBold.ttf"
        if not os.path.exists(font_path):
            font = self._load_font(80)
        else:
            font = ImageFont.truetype(font_path, 80)
        
        words = hook_phrase.split()
        if len(words) >= 3:
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
        else:
            line1 = hook_phrase
            line2 = ""
            
        text_x = 85
        text_y = 170
        
        def draw_stroke_text(d, t, pos, fn, text_color):
            tx, ty = pos
            stroke = 5
            for dx in range(-stroke, stroke+1):
                for dy in range(-stroke, stroke+1):
                    if dx == 0 and dy == 0: continue
                    d.text((tx+dx, ty+dy), t, font=fn, fill=(0, 0, 0, 255))
            d.text((tx, ty), t, font=fn, fill=text_color)
            
        draw_stroke_text(draw, line1, (text_x, text_y), font, (255, 255, 255))
        if line2:
            draw_stroke_text(draw, line2, (text_x, text_y + 110), font, (0, 240, 255))
            
        # 6. Draw Bottom Supporting Fact Strip
        strip_h = 75
        strip_y = 720 - strip_h
        
        strip_overlay = Image.new("RGBA", self.size, (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(strip_overlay)
        s_draw.rectangle([(0, strip_y), (1280, 720)], fill=(10, 22, 40, 255))
        s_draw.rectangle([(0, strip_y), (1280, strip_y + 4)], fill=(0, 240, 255, 255))
        
        canvas = Image.alpha_composite(canvas.convert("RGBA"), strip_overlay).convert("RGB")
        draw = ImageDraw.Draw(canvas)
        
        reg_font_path = "automation/fonts/Barlow-Regular.ttf"
        if not os.path.exists(reg_font_path):
            reg_font = self._load_font(22)
        else:
            reg_font = ImageFont.truetype(reg_font_path, 22)
            
        fact_text = supporting_fact
        if len(fact_text) > 95:
            fact_text = fact_text[:92] + "..."
            
        try:
            fw = reg_font.getbbox(fact_text)[2] - reg_font.getbbox(fact_text)[0]
        except AttributeError:
            fw = reg_font.getsize(fact_text)[0]
            
        fx = (1280 - fw) // 2
        fy = strip_y + (strip_h - 22) // 2
        
        draw.text((fx + 1, fy + 1), fact_text, font=reg_font, fill=(0, 0, 0, 200))
        draw.text((fx, fy), fact_text, font=reg_font, fill=(230, 245, 255))
        
        canvas.save(output_path, "JPEG", quality=95)
        print(f"[Thumbnail] Premium science thumbnail successfully written to {output_path}")
        return output_path

    def _fetch_ai_background(self, prompt: str) -> str:
        """Fetches a high-quality background from Pollinations.ai."""
        clean_prompt = re.sub(r'[^a-zA-Z0-9 ]', ' ', prompt).strip()
        full_prompt = f"cinematic 4k high contrast {clean_prompt}, vibrant colors, photorealistic, no people, no text"
        encoded = requests.utils.quote(full_prompt)
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&seed={seed}&nologo=true"
        
        save_path = os.path.join(self.output_dir, "temp_bg.jpg")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                return save_path
        except Exception as e:
            print(f"Error fetching thumbnail background: {e}")
        return None

    def _load_font(self, fsize=120):
        # Cross-platform robust font list
        font_paths = []
        if os.name == 'nt':
            windir = os.environ.get('WINDIR', 'C:\\Windows')
            font_paths += [
                os.path.join(windir, 'Fonts', 'ariblk.ttf'), # Arial Black
                os.path.join(windir, 'Fonts', 'impact.ttf'), # Impact
                os.path.join(windir, 'Fonts', 'arialbd.ttf'), # Arial Bold
                os.path.join(windir, 'Fonts', 'segoeuib.ttf'), # Segoe UI Bold
            ]
        else:
            font_paths += [
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        
        # Then custom assets
        font_paths += [
            "automation/media/assets/Montserrat-Black.ttf",
            "automation/media/assets/NotoSansDevanagari-Regular.ttf"
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, fsize)
                except: continue
        
        # Ultimate fallback for Windows
        if os.name == 'nt':
             return ImageFont.truetype("arial.ttf", fsize)
             
        return ImageFont.load_default()

    def _draw_dynamic_text(self, draw, text, font):
        """Draws large, high-contrast text with shadow and border."""
        W, H = self.size
        # Split text into lines if too long
        words = text.split()
        lines = []
        if len(words) > 3:
            lines.append(" ".join(words[:2]))
            lines.append(" ".join(words[2:]))
        else:
            lines.append(text)

        total_h = sum([draw.textbbox((0,0), line, font=font)[3] for line in lines]) + (len(lines)-1)*20
        y = (H - total_h) // 2

        for line in lines:
            bbox = draw.textbbox((0,0), line, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = (W - w) // 2
            
            # Draw Shadow
            draw.text((x+8, y+8), line, font=font, fill=(0,0,0,180))
            
            # Draw Thick Border (Stroke)
            stroke_width = 6
            for dx in range(-stroke_width, stroke_width+1):
                for dy in range(-stroke_width, stroke_width+1):
                    draw.text((x+dx, y+dy), line, font=font, fill='black')
            
            # Draw Main Text (Vibrant Yellow or White)
            draw.text((x, y), line, font=font, fill='#FFD700')
            y += h + 30

    def _add_branding(self, img):
        logo_path = "automation/media/assets/nepal_now_logo.png"
        if os.path.exists(logo_path):
            logo = Image.open(logo_path).convert("RGBA")
            logo.thumbnail((150, 150))
            img.paste(logo, (50, 50), logo)
