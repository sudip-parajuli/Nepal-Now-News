import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure the root workspace directory is in the import path
sys.path.append(os.getcwd())

from automation.config_loader import ConfigLoader
from automation.pipelines.science_pipeline import SciencePipeline

load_dotenv()

async def run_smoke_test():
    print("==================================================")
    print("STARTING E2E PIPELINE SMOKE TEST: Bismuth Crystals")
    print("==================================================")
    
    # Verify environment variables
    gemini_key = os.getenv("GEMINI_API_KEY")
    hf_token = os.getenv("HF_TOKEN")
    
    if not gemini_key:
        print("CRITICAL WARNING: GEMINI_API_KEY environment variable is not set!")
    else:
        print("GEMINI_API_KEY: FOUND")
        
    if not hf_token:
        print("CRITICAL WARNING: HF_TOKEN environment variable is not set! HF video generation will fall back to secondary model or fail.")
    else:
        print("HF_TOKEN: FOUND")
        
    # Verify font assets are present
    fonts_dir = "automation/fonts"
    required_fonts = ["Barlow-CondensedBold.ttf", "Barlow-Bold.ttf", "Barlow-Regular.ttf"]
    print("\nChecking fonts:")
    for font in required_fonts:
        fpath = os.path.join(fonts_dir, font)
        if os.path.exists(fpath):
            print(f" - {font}: OK")
        else:
            print(f" - {font}: MISSING!")
            
    # Load science config
    config_path = "automation/config/science.yaml"
    if not os.path.exists(config_path):
        print(f"CRITICAL ERROR: Config file '{config_path}' is missing.")
        return
        
    config = ConfigLoader.load_config(config_path)
    
    # Bypass slow Hugging Face video queues for fast local visual E2E validation
    os.environ["HF_TOKEN"] = ""
    
    # Initialize the Science Pipeline
    pipeline = SciencePipeline(config)
    
    # Force clean slate for temp assets to ensure full 9-scene generation
    import shutil
    print("\n[Smoke Test] Cleaning up existing temporary assets for a clean-slate run...")
    shutil.rmtree("automation/storage/temp_videos", ignore_errors=True)
    shutil.rmtree("automation/storage/temp_images", ignore_errors=True)
    os.makedirs("automation/storage/temp_videos", exist_ok=True)
    os.makedirs("automation/storage/temp_images", exist_ok=True)
    
    # Override topic generation and run both daily summary and shorts end-to-end in test mode
    topic = "Bismuth Crystals"
    try:
        await pipeline._run_daily(topic=topic, is_test=True)
        print("\n==================================================")
        print("SMOKE TEST 1 COMPLETE: DAILY SUMMARY RENDERED SUCCESSFULLY!")
        print("==================================================")
        
        await pipeline._run_shorts(topic=topic, is_test=True)
        print("\n==================================================")
        print("SMOKE TEST 2 COMPLETE: SHORTS RENDERED SUCCESSFULLY!")
        print("==================================================")
    except Exception as e:
        print("\n==================================================")
        print(f"SMOKE TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
