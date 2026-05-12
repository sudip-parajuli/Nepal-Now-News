import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from automation.content.script_writer import ScriptWriter
from automation.media.thumbnail_generator import ThumbnailGenerator

load_dotenv()

def test_thumbnail():
    writer = ScriptWriter(os.getenv("GEMINI_API_KEY"))
    gen = ThumbnailGenerator()
    
    topic = "The Science of Bismuth Crystals"
    script = "Bismuth is a fascinating element. When it melts and cools, it forms incredible iridescent hopper crystals..."
    
    print("Generating thumbnail info...")
    info = writer.generate_thumbnail_info(topic, script)
    print(f"Info: {info}")
    
    print("Generating thumbnail image...")
    path = gen.generate_thumbnail(info)
    print(f"Thumbnail created at: {path}")

if __name__ == "__main__":
    test_thumbnail()
