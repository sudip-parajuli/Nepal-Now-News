from moviepy.editor import TextClip
import os

def test_render():
    print("Testing TextClip rendering...")
    txt = "DIAGNOSTIC TEST: HELLO WORLD"
    fonts = ['Arial', 'Tahoma', 'Verdana', 'Courier New', 'Nirmala UI']
    
    for font in fonts:
        try:
            print(f"Trying font: {font}")
            clip = TextClip(txt, fontsize=70, color='white', font=font, method='label')
            output = f"debug_text_{font.replace(' ', '_')}.png"
            clip.save_frame(output, t=0)
            if os.path.exists(output) and os.path.getsize(output) > 1000:
                print(f"SUCCESS: Rendered with {font} to {output}")
            else:
                print(f"FAILURE: File produced but empty/small for {font}")
        except Exception as e:
            print(f"CRASH: Failed to render with {font}: {e}")

if __name__ == "__main__":
    test_render()
