import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append(os.getcwd())
from automation.config_loader import ConfigLoader
from automation.pipelines.science_pipeline import SciencePipeline

load_dotenv()

async def run_shorts_only():
    print("==================================================")
    print("STARTING E2E SHORTS ONLY SMOKE TEST")
    print("==================================================")
    
    config = ConfigLoader.load_config("automation/config/science.yaml")
    os.environ["HF_TOKEN"] = "" # Disable HF to speed up fallback
    
    pipeline = SciencePipeline(config)
    topic = "Bismuth Crystals Shorts Test"
    try:
        await pipeline._run_shorts(topic=topic, is_test=True)
        print("\n==================================================")
        print("SHORTS ONLY SMOKE TEST COMPLETE!")
        print("==================================================")
    except Exception as e:
        print("\n==================================================")
        print(f"SMOKE TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_shorts_only())
