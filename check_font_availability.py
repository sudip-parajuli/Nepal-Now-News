import os
from PIL import ImageFont

def check_fonts():
    windir = os.environ.get('WINDIR', 'C:\\Windows')
    font_paths = [
        os.path.join(windir, 'Fonts', 'Nirmala.ttc'),
        os.path.join(windir, 'Fonts', 'aparaj.ttf'),
        os.path.join(windir, 'Fonts', 'Nirmala.ttf'),
        os.path.join(windir, 'Fonts', 'NirmalaB.ttf'),
        os.path.join(windir, 'Fonts', 'NirmalaUI.ttf'),
        os.path.join(windir, 'Fonts', 'mangal.ttf'),
        os.path.join(windir, 'Fonts', 'utsaah.ttf'),
        os.path.join(windir, 'Fonts', 'arialbd.ttf'), 
    ]
    
    for path in font_paths:
        exists = os.path.exists(path)
        print(f"Path: {path}")
        print(f"  Exists: {exists}")
        if exists:
            try:
                font = ImageFont.truetype(path, 20)
                print(f"  Pillow Load: SUCCESS")
            except Exception as e:
                print(f"  Pillow Load: FAILED ({e})")
        print("-" * 20)

if __name__ == "__main__":
    check_fonts()
