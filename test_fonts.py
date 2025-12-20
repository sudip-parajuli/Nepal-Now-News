from moviepy.editor import TextClip
import os

def test_font(font_name, text="नमस्कार"):
    print(f"Testing font: {font_name} with text: {text}")
    try:
        clip = TextClip(text, fontsize=100, color='white', font=font_name, method='label')
        clip.write_videofile(f"storage/font_test_{font_name}.mp4", fps=24, logger=None)
        print(f"Success: {font_name}")
    except Exception as e:
        print(f"Error: {font_name} - {e}")

if __name__ == "__main__":
    if not os.path.exists("storage"):
        os.makedirs("storage")
    
    # Common Devanagari fonts on Windows
    fonts = [
        "Nirmala-UI",
        "Nirmala-UI-Bold",
        "Devanagari-MT",
        "Mangal",
        "Utsaah",
        "Arial", # Should fail to show Nepali
    ]
    
    for f in fonts:
        test_font(f)
