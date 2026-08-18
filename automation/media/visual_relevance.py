"""
AI-based relevance check for fetched b-roll: rejects a stock photo/video that doesn't
actually depict what the scene's narration is about, using Gemini's vision capability
(the same provider/keys already used for script and scene generation, so no new API
key is required). Deliberately fails OPEN — if the check itself errors out (quota,
network, model unavailable), the candidate is treated as relevant rather than blocking
the pipeline. A plausibly-relevant image that skipped verification beats a hard
pipeline failure; the goal is to catch the CLEARLY wrong ones DDG/Pexels/Pixabay
occasionally return for garbled or generic queries, not to guarantee perfection.
"""
import os
import re

_MODEL_CANDIDATES = ['gemini-flash-latest', 'gemini-2.5-flash', 'gemini-2.0-flash']
_MAX_BYTES = 4 * 1024 * 1024  # keep the vision request small/fast


def _get_client():
    try:
        from google import genai
    except ImportError:
        return None
    for key_name in ("GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3"):
        val = os.getenv(key_name, "").strip()
        if val:
            try:
                return genai.Client(api_key=val)
            except Exception:
                continue
    return None


def _extract_frame_if_video(path: str) -> str:
    """Returns a still-image path to check: `path` itself for images, or a temp JPEG
    frame extracted from a video. Returns None if extraction fails."""
    if not path.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        return path
    try:
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(path)
        frame_path = path + "_relevance_frame.jpg"
        clip.save_frame(frame_path, t=min(0.5, max(0.0, clip.duration / 2)))
        clip.close()
        return frame_path
    except Exception as e:
        print(f"[VisualRelevance] Frame extraction failed for {path}: {e}")
        return None


def is_visually_relevant(asset_path: str, description: str, strict: bool = False) -> bool:
    """
    Returns True if the image (or video's mid-frame) plausibly depicts `description`.
    Fails open (returns True) whenever the check can't actually run or errors out.
    `strict=True` asks the model to be more skeptical — used when we already have a
    generous pool of candidates, so it's safe to be pickier about which one wins.
    """
    if not description or not description.strip():
        return True
    if not asset_path or not os.path.exists(asset_path):
        return True

    client = _get_client()
    if not client:
        return True

    still_path = _extract_frame_if_video(asset_path)
    if not still_path or not os.path.exists(still_path):
        return True

    try:
        if os.path.getsize(still_path) > _MAX_BYTES:
            return True  # skip check rather than upload something huge; not worth the latency
        with open(still_path, "rb") as f:
            img_bytes = f.read()
    except Exception as e:
        print(f"[VisualRelevance] Could not read {still_path}: {e}")
        return True
    finally:
        if still_path != asset_path and os.path.exists(still_path):
            try:
                os.remove(still_path)
            except OSError:
                pass

    clean_desc = re.sub(r'\*', '', description).strip()[:300]
    strictness = (
        "Be reasonably strict — reject generic stock footage that doesn't specifically "
        "relate to the subject, not just anything vaguely in the same category."
        if strict else
        "Be lenient — accept anything plausibly related, only reject images that are "
        "clearly about something else entirely."
    )
    prompt = (
        f"A video narrator is saying: \"{clean_desc}\"\n"
        f"Does this image plausibly illustrate or relate to that? {strictness}\n"
        "Answer with exactly one word: YES or NO."
    )

    try:
        from google.genai import types
    except ImportError:
        return True

    for model_id in _MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )
            answer = (response.text or "").strip().upper()
            return answer.startswith("Y")
        except Exception as e:
            err = str(e).lower()
            if "404" in err and ("model" in err or "not_found" in err):
                continue  # try the next candidate model
            print(f"[VisualRelevance] Check failed ({model_id}): {str(e)[:150]}")
            return True  # fail open on quota/transient/unexpected errors

    return True
