import os
import time
import json
import datetime
import subprocess
import requests

HF_API_URL = "https://api-inference.huggingface.co/models/THUDM/CogVideoX-2b"
HF_USAGE_FILE = "automation/storage/hf_usage.json"
HF_MONTHLY_LIMIT = 900  # Hard stop at 900 to leave 100 as buffer


def _load_usage() -> dict:
    """Load the HF usage counter from disk, reset if month has changed."""
    today = datetime.date.today()
    current_month = today.strftime("%Y-%m")
    if os.path.exists(HF_USAGE_FILE):
        try:
            with open(HF_USAGE_FILE, "r") as f:
                data = json.load(f)
            if data.get("month") == current_month:
                return data
        except Exception:
            pass
    # New month or missing file — reset
    return {"month": current_month, "count": 0}


def _save_usage(data: dict):
    os.makedirs(os.path.dirname(HF_USAGE_FILE), exist_ok=True)
    with open(HF_USAGE_FILE, "w") as f:
        json.dump(data, f)


def _quota_ok() -> bool:
    """Return True if we still have HF quota this month."""
    usage = _load_usage()
    if usage["count"] >= HF_MONTHLY_LIMIT:
        print(f"[HFVideoGen] WARNING: HF quota exhausted for {usage['month']} "
              f"({usage['count']}/{HF_MONTHLY_LIMIT}). Skipping AI video generation.")
        return False
    return True


def _increment_quota():
    usage = _load_usage()
    usage["count"] += 1
    _save_usage(usage)
    print(f"[HFVideoGen] HF usage this month: {usage['count']}/{HF_MONTHLY_LIMIT}")


def _validate_video_ffprobe(filepath: str) -> bool:
    """
    Use FFprobe to validate the downloaded video.
    Returns True if the file contains a valid video stream.
    Logs the codec name for debugging.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_name",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True, text=True, timeout=15
        )
        codec = result.stdout.strip()
        if result.returncode != 0 or not codec:
            print(f"[HFVideoGen] FFprobe error or no video stream. stderr: {result.stderr[:200]}")
            return False
        print(f"[HFVideoGen] Video codec detected: {codec}")
        supported = {"h264", "hevc", "vp8", "vp9", "av1", "mpeg4"}
        if codec.lower() not in supported:
            print(f"[HFVideoGen] Unsupported codec '{codec}' — MoviePy may reject this file.")
            return False
        return True
    except FileNotFoundError:
        print("[HFVideoGen] WARNING: ffprobe not found. Skipping codec validation.")
        # If ffprobe isn't available, do a basic size check instead
        return os.path.getsize(filepath) > 10_000
    except Exception as e:
        print(f"[HFVideoGen] FFprobe validation error: {e}")
        return False


def _fallback_pollinations_image(prompt: str, output_dir: str, scene_idx: int) -> str | None:
    """Generate a fallback image via Pollinations.ai when HF video fails."""
    import re
    clean_prompt = re.sub(r"[^a-zA-Z0-9 ]", " ", prompt).strip()
    full_prompt = f"cinematic 4k, {clean_prompt}, deep space, photorealistic, no people, dramatic lighting"
    encoded = requests.utils.quote(full_prompt)
    seed = (scene_idx * 31337) % 999999
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1280&height=720&seed={seed}&nologo=true"
    fallback_path = os.path.join(output_dir, f"scene_{scene_idx}_fallback.jpg")
    try:
        print(f"[HFVideoGen] Falling back to Pollinations.ai image for scene {scene_idx}...")
        resp = requests.get(url, timeout=90)
        if resp.status_code == 200 and len(resp.content) > 5000:
            with open(fallback_path, "wb") as f:
                f.write(resp.content)
            print(f"[HFVideoGen] Fallback image saved: {fallback_path}")
            return fallback_path
        else:
            print(f"[HFVideoGen] Pollinations fallback failed (status={resp.status_code})")
    except Exception as e:
        print(f"[HFVideoGen] Pollinations fallback error: {e}")
    return None


def generate_hf_video(prompt: str, output_dir: str, scene_idx: int, hf_token: str) -> dict:
    """
    Generate a short AI video clip via HuggingFace CogVideoX-2B free Inference API.

    Returns a dict:
      {"asset_type": "ai_video", "asset_path": "...mp4"}   — on success
      {"asset_type": "image",    "asset_path": "...jpg"}   — on fallback
      {"asset_type": "none",     "asset_path": None}       — if everything fails
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── Quota guard ───────────────────────────────────────────────────────────
    if not hf_token or not _quota_ok():
        fallback = _fallback_pollinations_image(prompt, output_dir, scene_idx)
        return {"asset_type": "image" if fallback else "none", "asset_path": fallback}

    headers = {"Authorization": f"Bearer {hf_token}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "num_frames": 48,
            "guidance_scale": 6.0,
            "num_inference_steps": 50,
        },
    }
    video_path = os.path.join(output_dir, f"scene_{scene_idx}_aivideo.mp4")

    # ── Retry loop ────────────────────────────────────────────────────────────
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"[HFVideoGen] Scene {scene_idx}: HF API attempt {attempt}/{max_retries} ...")
        try:
            resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=120)

            if resp.status_code == 200:
                with open(video_path, "wb") as f:
                    f.write(resp.content)

                if _validate_video_ffprobe(video_path):
                    _increment_quota()
                    print(f"[HFVideoGen] Scene {scene_idx}: AI video saved → {video_path}")
                    return {"asset_type": "ai_video", "asset_path": video_path}
                else:
                    print(f"[HFVideoGen] Scene {scene_idx}: Video validation failed. Using fallback.")
                    os.remove(video_path)
                    break  # No point retrying — the model output is bad

            elif resp.status_code == 503:
                # Model cold-starting on HF free tier — wait and retry
                wait = 20
                print(f"[HFVideoGen] 503 (cold-start). Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            elif resp.status_code == 429:
                # Rate-limited — exponential backoff
                wait = 20 * (2 ** (attempt - 1))  # 20s, 40s, 80s
                print(f"[HFVideoGen] 429 (rate limit). Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            else:
                print(f"[HFVideoGen] Unexpected status {resp.status_code}: {resp.text[:200]}")
                break

        except requests.exceptions.Timeout:
            print(f"[HFVideoGen] Scene {scene_idx}: Request timed out (attempt {attempt}).")
            if attempt < max_retries:
                time.sleep(15)
        except Exception as e:
            print(f"[HFVideoGen] Scene {scene_idx}: Unexpected error: {e}")
            break

    # ── All retries exhausted → fallback ─────────────────────────────────────
    fallback = _fallback_pollinations_image(prompt, output_dir, scene_idx)
    return {"asset_type": "image" if fallback else "none", "asset_path": fallback}
