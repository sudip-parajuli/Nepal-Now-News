import asyncio
import os
from processors.rewrite_breaking import ScriptRewriter
from media.tts_english import TTSEngine
from media.video_long import VideoLongGenerator
from media.image_fetcher import ImageFetcher
from dotenv import load_dotenv

load_dotenv()

async def verify_refined_summary():
    print("--- Verifying Refined Daily Summary ---")
    if not os.path.exists("storage/test"):
        os.makedirs("storage/test")

    # 1. Mock news items
    mock_news = [
        {
            "headline": "काठमाडौंमा ट्राफिक जाम कम गर्न नयाँ नियम",
            "content": "काठमाडौं उपत्यकामा ट्राफिक जाम कम गर्न महानगरपालिकाले नयाँ ट्राफिक नियम लागु गरेको छ। अब व्यस्त समयमा ठूला सवारी साधनलाई रोक लगाइनेछ।"
        },
        {
            "headline": "नेपाल र भारतबीच उर्जा सम्झौता",
            "content": "नेपाल र भारतबीच आगामी १० वर्षमा १० हजार मेगावाट विद्युत व्यापार गर्ने ऐतिहासिक सम्झौता भएको छ।"
        }
    ]

    rewriter = ScriptRewriter(os.getenv("GEMINI_API_KEY"))
    img_fetcher = ImageFetcher()
    vgen = VideoLongGenerator()

    # 2. Generate structured script
    print("Generating structured script...")
    segments = rewriter.summarize_for_daily(mock_news)
    print(f"Segments generated: {len(segments)}")
    for s in segments:
        print(f" - [{s.get('type')}] Voice: {s.get('gender')} | Headline: {s.get('headline', 'N/A')}")

    # 3. Fetch images
    print("Fetching images...")
    for i, seg in enumerate(segments):
        if seg.get("type") == "news" and seg.get("headline"):
            keywords = rewriter.generate_image_keywords(seg["headline"])
            img_path = img_fetcher.fetch_image(keywords, f"storage/test/test_img_{i}.jpg")
            seg["image_path"] = img_path
        elif seg.get("type") == "intro":
            seg["image_path"] = img_fetcher.fetch_image("Nepali news studio", "storage/test/test_intro.jpg")

    # 4. Generate audio
    print("Generating multi-vocal audio...")
    audio_path = "storage/test/test_daily.mp3"
    _, offsets, durations = await TTSEngine.generate_multivocal_audio(segments, audio_path)
    print(f"Audio generated. Durations: {durations}")

    # 5. Create video
    print("Creating video...")
    video_path = "storage/test/test_daily.mp4"
    vgen.create_daily_summary(segments, audio_path, video_path, offsets, durations=durations)
    print(f"Video saved to: {video_path}")

if __name__ == "__main__":
    asyncio.run(verify_refined_summary())
