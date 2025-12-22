import asyncio
import edge_tts
import os
import sys

# Force UTF-8 for printing
sys.stdout.reconfigure(encoding='utf-8')

async def check_chunks(text, voice="en-US-ChristopherNeural", rate="+15%"):
    print(f"\nCHUNKS FOR: '{text}'")
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    
    async for chunk in communicate.stream():
        print(f"Type: {chunk.get('type')} | Keys: {list(chunk.keys())}")
        if chunk.get('type') == 'WordBoundary':
            # Don't print the whole chunk if it has binary data, but WordBoundary shouldn't
            print(f"  -> WordBoundary detail: text={chunk.get('text')}, offset={chunk.get('offset')}, duration={chunk.get('duration')}")

if __name__ == "__main__":
    asyncio.run(check_chunks("Hello world"))
