from PIL import Image, ImageDraw, ImageFont
import os

def test_nepali_rendering():
    font_path = "automation/media/assets/NotoSansDevanagari-Regular.ttf"
    if not os.path.exists(font_path):
        print(f"ERROR: Font not found at {font_path}")
        return

    text = "नमस्ते! नेपाली फन्ट परीक्षण।"
    try:
        font = ImageFont.truetype(font_path, 60)
        # Measure text
        dummy = Image.new('RGB', (1, 1))
        draw = ImageDraw.Draw(dummy)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        # Create image
        img = Image.new('RGB', (tw + 40, th + 40), color='white')
        d = ImageDraw.Draw(img)
        d.text((20, 20), text, font=font, fill='black')
        
        output_path = "nepali_font_verification.png"
        img.save(output_path)
        print(f"SUCCESS: Rendered Nepali text to {output_path}")
        print(f"Text size: {tw}x{th}")
    except Exception as e:
        print(f"FAILED: Rendering error: {e}")

if __name__ == "__main__":
    test_nepali_rendering()
