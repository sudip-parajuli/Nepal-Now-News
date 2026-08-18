import os
import json
import uuid
import datetime
from typing import List, Dict

from .hf_video_generator import generate_hf_video
from .image_fetcher import ImageFetcher
from . import stock_media

MAX_AI_VIDEO_PER_JOB = 3     # Per-video cap to protect HF monthly quota
MAX_STOCK_VIDEO_PER_JOB = 5  # Per-video cap to keep download/render time bounded


class AssetOrchestrator:
    """
    Routes visual scenes to the correct asset generator and writes a
    job-scoped asset_manifest.json to automation/storage/temp_videos/{job_id}/.

    Supports resume: if a manifest already exists for the same topic+date,
    it re-uses it instead of re-fetching all assets.
    """

    def __init__(self, hf_token: str = None):
        self.hf_token = hf_token or os.getenv("HF_TOKEN", "")
        self.image_fetcher = ImageFetcher()

    # ── Public API ─────────────────────────────────────────────────────────────

    def fetch_all(self, scenes: List[Dict], topic: str, aspect_ratio: str = '16:9') -> dict:
        """
        Process all scenes and return the full job manifest dict with all 6 visual types.
        """
        today = datetime.date.today().isoformat()

        # ── Resume support: check for existing manifest ────────────────────────
        existing = self._find_existing_manifest(topic, today)
        if existing and existing.get("aspect_ratio") == aspect_ratio:
            print(f"[AssetOrchestrator] Resuming from existing manifest: {existing['job_id']}")
            return existing

        # ── New job ────────────────────────────────────────────────────────────
        job_id = str(uuid.uuid4())[:12]
        job_dir = os.path.join("automation", "storage", "temp_videos", job_id)
        os.makedirs(job_dir, exist_ok=True)

        manifest = {
            "job_id": job_id,
            "job_dir": job_dir,
            "topic": topic,
            "date": today,
            "aspect_ratio": aspect_ratio,
            "scenes": [],
        }

        ai_video_count = 0    # Per-video budget tracker
        stock_video_count = 0  # Real stock-video b-roll budget tracker

        for idx, scene in enumerate(scenes):
            visual_type = scene.get("visual_type", "image")
            narration = scene.get("narration", "")
            image_cue = scene.get("image_cue")
            if not image_cue or image_cue == "None":
                # Generic fallback — previously hardcoded "{topic} space astronomy" here, which
                # meant any scene missing an image_cue (regardless of the video's actual subject —
                # chemistry, biology, neuroscience...) silently searched for space photos instead.
                image_cue = f"{topic} science"
            
            ai_video_prompt = scene.get("ai_video_prompt", "")

            # ── Schema Defaults & Downgrades ──────────────────────────────────
            if visual_type == "kinetic_stat" and not scene.get("stat_data"):
                print(f"[AssetOrchestrator] Scene {idx}: Downgrading kinetic_stat to typewriter_text due to missing stat_data")
                visual_type = "typewriter_text"
            if visual_type == "data_bars" and not scene.get("bar_data"):
                print(f"[AssetOrchestrator] Scene {idx}: Downgrading data_bars to typewriter_text due to missing bar_data")
                visual_type = "typewriter_text"

            emphasis_phrase = scene.get("emphasis_phrase")
            if not emphasis_phrase or emphasis_phrase == "None":
                emphasis_phrase = scene.get("question_text", "")[:20] if scene.get("question_text") else ""

            typewriter_words = scene.get("typewriter_words")
            if not typewriter_words:
                typewriter_words = [{"word": w, "weight": "md"} for w in narration.split()]

            scene_entry = {
                "scene_idx": idx,
                "visual_type": visual_type,
                "asset_type": "none",
                "asset_path": None,
                "narration": narration,
                "image_cue": image_cue,
                # Store all custom fields for the 6 styles
                "typewriter_words": typewriter_words,
                "stat_data": scene.get("stat_data"),
                "named_entity": scene.get("named_entity"),
                "ai_video_prompt": ai_video_prompt,
                "question_text": scene.get("question_text"),
                "emphasis_phrase": emphasis_phrase,
                "bar_data": scene.get("bar_data")
            }

            # ── Route by visual_type ─────────────────────────────────────────
            if visual_type == "ai_video":
                if ai_video_count >= MAX_AI_VIDEO_PER_JOB:
                    print(f"[AssetOrchestrator] Scene {idx}: ai_video budget cap reached "
                          f"({MAX_AI_VIDEO_PER_JOB}/job). Downgrading to image.")
                    visual_type = "image"  # fall through to image fetch below
                else:
                    print(f"[AssetOrchestrator] Scene {idx}: ai_video -> HF CogVideoX-2B "
                          f"({ai_video_count+1}/{MAX_AI_VIDEO_PER_JOB})")
                    result = generate_hf_video(
                        prompt=ai_video_prompt or image_cue,
                        output_dir=job_dir,
                        scene_idx=idx,
                        hf_token=self.hf_token,
                    )
                    
                    if result["asset_type"] == "ai_video":
                        asset_path = result["asset_path"]
                        if aspect_ratio == "9:16":
                            asset_path = self._crop_video_to_portrait(asset_path)
                            
                        scene_entry["asset_type"] = "ai_video"
                        scene_entry["asset_path"] = asset_path
                        ai_video_count += 1
                        manifest["scenes"].append(scene_entry)
                        self._save_manifest(manifest)
                        continue
                    else:
                        visual_type = "image"  # If video failed, treat as image

            # Real stock-video b-roll for plain "image" scenes — an actual moving clip
            # that matches the subject beats a static Ken-Burns photo, and Pexels/Pixabay
            # are official APIs (not scraping), so this doesn't add DDG rate-limit risk.
            # Skipped entirely (falls through to the image fetch below) when no API key
            # is configured, or once the per-job budget is used up.
            if (visual_type == "image" and stock_media.has_stock_api_keys()
                    and stock_video_count < MAX_STOCK_VIDEO_PER_JOB):
                print(f"[AssetOrchestrator] Scene {idx}: trying real stock-video b-roll for '{image_cue}'...")
                video_paths = stock_media.fetch_real_videos(
                    image_cue, 1, job_dir, f"job_{job_id}_scene{idx}",
                    portrait=(aspect_ratio == "9:16"),
                )
                if video_paths:
                    asset_path = video_paths[0]
                    if aspect_ratio == "9:16":
                        asset_path = self._crop_video_to_portrait(asset_path)
                    scene_entry["asset_type"] = "video"
                    scene_entry["asset_path"] = asset_path
                    stock_video_count += 1
                    manifest["scenes"].append(scene_entry)
                    self._save_manifest(manifest)
                    continue

            # Fetch background image for all other scene types to draw overlay styles on top of
            print(f"[AssetOrchestrator] Scene {idx}: fetching background image for type '{visual_type}'...")
            # Second query used to always append "space astronomy" regardless of topic, which
            # dragged every non-space scene (chemistry, biology, psychology...) toward irrelevant
            # deep-space b-roll. Use a topic-neutral second phrasing instead.
            queries = [
                f"{image_cue} cinematic 4k",
                f"{image_cue} documentary photography",
            ]
            # Sleep slightly to avoid DDG rate limits between scenes
            if idx > 0:
                import time
                time.sleep(2.5)
            paths = self.image_fetcher.fetch_multi_images(
                queries,
                base_filename=f"job_{job_id}_scene{idx}",
                topic_context=topic,
                portrait=(aspect_ratio == "9:16"),
            )
            if paths:
                asset_path = paths[0]
                if aspect_ratio == "9:16":
                    asset_path = self._crop_image_to_portrait(asset_path)
                scene_entry["asset_type"] = "image"
                scene_entry["asset_path"] = asset_path
            else:
                scene_entry["asset_type"] = "none"
                scene_entry["asset_path"] = None

            manifest["scenes"].append(scene_entry)
            self._save_manifest(manifest)

        print(f"[AssetOrchestrator] Job {job_id} complete. "
              f"{ai_video_count} AI video clip(s), "
              f"{stock_video_count} real stock-video clip(s), "
              f"{sum(1 for s in manifest['scenes'] if s['asset_type']=='image')} image background(s).")
        return manifest

    def _crop_image_to_portrait(self, img_path: str) -> str:
        try:
            from PIL import Image
            img = Image.open(img_path).convert("RGB")
            w, h = img.size
            target_w = int(h * 9 / 16)
            if target_w < w:
                x_offset = (w - target_w) // 2
                img = img.crop((x_offset, 0, x_offset + target_w, h))
            img = img.resize((1080, 1920), Image.Resampling.LANCZOS)
            img.save(img_path)
            return img_path
        except Exception as e:
            print(f"[AssetOrchestrator] Error cropping image {img_path}: {e}")
            return img_path

    def _crop_video_to_portrait(self, vid_path: str) -> str:
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(vid_path)
            w, h = clip.size
            target_w = int(h * 9 / 16)
            if target_w < w:
                x1 = (w - target_w) // 2
                clip = clip.crop(x1=x1, y1=0, x2=x1+target_w, y2=h)
            clip = clip.resize(newsize=(1080, 1920))
            new_path = vid_path.replace(".mp4", "_portrait.mp4")
            clip.write_videofile(new_path, codec="libx264", audio=False, logger=None)
            clip.close()
            return new_path
        except Exception as e:
            print(f"[AssetOrchestrator] Error cropping video {vid_path}: {e}")
            return vid_path

    def cleanup(self, manifest: dict):
        """Delete the entire temp/{job_id}/ directory after a successful render."""
        job_dir = manifest.get("job_dir", "")
        if job_dir and os.path.isdir(job_dir):
            import shutil
            shutil.rmtree(job_dir, ignore_errors=True)
            print(f"[AssetOrchestrator] Cleaned up temp dir: {job_dir}")

    # ── Internals ──────────────────────────────────────────────────────────────

    def _save_manifest(self, manifest: dict):
        path = os.path.join(manifest["job_dir"], "manifest.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _find_existing_manifest(self, topic: str, date: str) -> dict | None:
        """
        Search all existing job dirs for a manifest matching topic+date.
        Returns the manifest if found and all asset_paths still exist on disk.
        """
        base = os.path.join("automation", "storage", "temp_videos")
        if not os.path.isdir(base):
            return None
        for job_id in os.listdir(base):
            manifest_path = os.path.join(base, job_id, "manifest.json")
            if not os.path.exists(manifest_path):
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    m = json.load(f)
                if m.get("topic") == topic and m.get("date") == date:
                    # Verify all file-backed assets still exist
                    all_ok = all(
                        s["asset_path"] is None or os.path.exists(s["asset_path"])
                        for s in m.get("scenes", [])
                    )
                    if all_ok:
                        return m
            except Exception:
                continue
        return None
