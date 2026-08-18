"""
Adds a small, unobtrusive channel-handle watermark to images posted to Facebook/
Instagram — so a photo re-shared off-platform is still traceable back to the channel.
"""
import os
from PIL import Image, ImageDraw, ImageFont

_FONT_PATHS = [
    "automation/fonts/Barlow-Bold.ttf",
    "automation/fonts/Barlow-CondensedBold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def add_watermark(image_path: str, text: str = "@dailydeepspace", output_path: str = None,
                   position: str = "bottom-right") -> str:
    """
    Draws `text` in a small semi-transparent pill in one corner of the image.
    Returns the path written to (a new file unless output_path == image_path).
    On any failure, returns the original image_path unchanged (never blocks posting).
    """
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size

        font_size = max(16, int(min(w, h) * 0.028))
        font = _get_font(font_size)

        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        try:
            bbox = font.getbbox(text)
            text_w, text_h, text_top = bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[1]
        except AttributeError:
            text_w, text_h, text_top = draw.textlength(text, font=font), font_size, 0

        pad_x, pad_y = int(font_size * 0.7), int(font_size * 0.45)
        margin = int(min(w, h) * 0.035)
        pill_w, pill_h = text_w + pad_x * 2, text_h + pad_y * 2

        if position == "bottom-right":
            x0, y0 = w - margin - pill_w, h - margin - pill_h
        elif position == "bottom-left":
            x0, y0 = margin, h - margin - pill_h
        elif position == "top-right":
            x0, y0 = w - margin - pill_w, margin
        else:  # top-left
            x0, y0 = margin, margin

        # A radius too close to pill_h/2 leaves a near-zero-height middle strip that
        # some Pillow versions (e.g. 9.5) fail to rasterize (raises "y1 must be
        # greater than or equal to y0" from an internal degenerate rectangle piece).
        # Capping well below half the height avoids the edge case entirely.
        pill_radius = max(4, pill_h // 2 - 4)
        draw.rounded_rectangle(
            [(x0, y0), (x0 + pill_w, y0 + pill_h)],
            radius=pill_radius, fill=(0, 0, 0, 130),
        )
        draw.text(
            (x0 + pad_x, y0 + pad_y - text_top),
            text, font=font, fill=(255, 255, 255, 235),
        )

        watermarked = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        out_path = output_path or image_path
        watermarked.save(out_path, "JPEG", quality=92)
        return out_path
    except Exception as e:
        print(f"[Watermark] Failed to watermark {image_path}: {e}")
        return image_path
