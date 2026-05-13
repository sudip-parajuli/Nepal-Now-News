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
        Generates a thumbnail image with AI background and text overlay.
        info: {'text': '...', 'image_prompt': '...'}
        """
        text = info.get('text', 'Amazing Science').upper()
        image_prompt = info.get('image_prompt', 'cinematic science background')
        
        if not output_path:
            clean_text = re.sub(r'[^a-zA-Z0-9]', '_', text)[:20]
            output_path = os.path.join(self.output_dir, f"thumb_{clean_text}.jpg")

        # 1. Generate/Fetch Background
        bg_path = self._fetch_ai_background(image_prompt)
        if not bg_path:
            # Fallback to solid color if everything fails
            img = Image.new('RGB', self.size, color=(15, 25, 45))
        else:
            img = Image.open(bg_path).resize(self.size, Image.Resampling.LANCZOS)
            # Add a slight blur to make text pop
            # img = img.filter(ImageFilter.GaussianBlur(radius=1))

        draw = ImageDraw.Draw(img)
        
        # 2. Load Font
        font = self._load_font(fsize=120)
        
        # 3. Draw Text with Shadow and Stroke
        self._draw_dynamic_text(draw, text, font)
        
        # 4. Add Branding (Optional)
        # self._add_branding(img)

        # 5. Save and Return
        img.save(output_path, "JPEG", quality=90)
        print(f"Thumbnail saved at: {output_path}")
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
