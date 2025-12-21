import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path to allow absolute imports within the automation package
sys.path.append(os.getcwd())

from automation.config_loader import ConfigLoader
from automation.pipelines.nepali_news_pipeline import NepaliNewsPipeline
from automation.pipelines.science_pipeline import SciencePipeline

load_dotenv()

async def list_channels():
    config_dir = "automation/config"
    if not os.path.exists(config_dir):
        print("No configs found.")
        return
    for f in os.listdir(config_dir):
        if f.endswith(".yaml"):
            print(f" - {f}")

async def main():
    parser = argparse.ArgumentParser(description="Multi-Channel Autonomous Media Platform")
    parser.add_argument("--config", help="Path to channel YAML config")
    parser.add_argument("--mode", default="breaking", choices=["breaking", "daily", "shorts"], help="Execution mode")
    parser.add_argument("--test", action="store_true", help="Run in test mode (skip upload)")
    parser.add_argument("--list", action="store_true", help="List available channels")
    
    args = parser.parse_args()

    if args.list:
        await list_channels()
        return

    if not args.config:
        parser.print_help()
        print("\nAvailable channels:")
        await list_channels()
        return

    # Load Config
    config = ConfigLoader.load_config(args.config)
    channel_type = config.get("type")

    # Route to Pipeline
    pipeline = None
    if channel_type == "news":
        pipeline = NepaliNewsPipeline(config)
    elif channel_type == "science":
        pipeline = SciencePipeline(config)
    else:
        print(f"Error: Unknown channel type '{channel_type}'")
        sys.exit(1)

    # Run Pipeline
    if pipeline:
        await pipeline.run(mode=args.mode, is_test=args.test)

if __name__ == "__main__":
    asyncio.run(main())
