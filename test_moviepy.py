from moviepy.editor import TextClip
import os

try:
    print("Testing TextClip...")
    # This will fail if ImageMagick is not configured
    clip = TextClip("Test", fontsize=70, color='white', size=(100, 100))
    print("TextClip works!")
except Exception as e:
    print(f"TextClip Error: {e}")
    print("\nAttempting to find ImageMagick binary...")
    # Common paths on Windows
    possible_paths = [
        r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
        r"C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe",
        r"C:\Program Files\ImageMagick-7.1.0-Q16\magick.exe"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found ImageMagick at: {path}")
            print("To fix, add this to your system PATH or configure it in MoviePy config_defaults.py")
            break
    else:
        print("ImageMagick not found in common locations.")
