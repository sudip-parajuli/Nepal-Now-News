import os
import json
import uuid
import datetime
from typing import List, Dict

from .hf_video_generator import generate_hf_video
from .image_fetcher import ImageFetcher

MAX_AI_VIDEO_PER_JOB = 3   # Per-video cap to protect HF monthly quota


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

    def fetch_all(self, scenes: List[Dict], topic: str) -> dict:
        """
        Process all scenes and return the full job manifest dict:
        {
          "job_id":   "...",
          "job_dir":  "automation/storage/temp_videos/{job_id}",
          "topic":    "...",
          "date":     "YYYY-MM-DD",
          "scenes":   [
              {
                "scene_idx":    0,
                "asset_type":   "ai_video" | "image" | "kinetic_text" | "none",
                "asset_path":   "path/to/file" or None,
                "kinetic_stat": {...} or None,
                "narration":    "..."
              },
              ...
          ]
        }
        """
        today = datetime.date.today().isoformat()

        # ── Resume support: check for existing manifest ────────────────────────
        existing = self._find_existing_manifest(topic, today)
        if existing:
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
            "scenes": [],
        }

        ai_video_count = 0  # Per-video budget tracker

        for idx, scene in enumerate(scenes):
            visual_type = scene.get("visual_type", "image")
            narration = scene.get("narration", "")
            kinetic_stat = scene.get("kinetic_stat")  # May be None
            image_cue = scene.get("image_cue", topic)
            ai_video_prompt = scene.get("ai_video_prompt", "")
            kinetic_overlay = scene.get("kinetic_overlay", False)  # ADD: overlay mode

            scene_entry = {
                "scene_idx": idx,
                "asset_type": "none",
                "asset_path": None,
                "kinetic_stat": kinetic_stat,
                "kinetic_overlay": kinetic_overlay,
                "narration": narration,
                "image_cue": image_cue,
            }

            # ── Route by visual_type ─────────────────────────────────────────
            if visual_type == "ai_video":
                if ai_video_count >= MAX_AI_VIDEO_PER_JOB:
                    print(f"[AssetOrchestrator] Scene {idx}: ai_video budget cap reached "
                          f"({MAX_AI_VIDEO_PER_JOB}/job). Downgrading to image.")
                    visual_type = "image"  # fall through to image fetch below
                else:
                    print(f"[AssetOrchestrator] Scene {idx}: ai_video → HF CogVideoX-2B "
                          f"({ai_video_count+1}/{MAX_AI_VIDEO_PER_JOB})")
                    result = generate_hf_video(
                        prompt=ai_video_prompt or image_cue,
                        output_dir=job_dir,
                        scene_idx=idx,
                        hf_token=self.hf_token,
                    )
                    scene_entry["asset_type"] = result["asset_type"]
                    scene_entry["asset_path"] = result["asset_path"]
                    if result["asset_type"] == "ai_video":
                        ai_video_count += 1
                    manifest["scenes"].append(scene_entry)
                    self._save_manifest(manifest)
                    continue

            if visual_type == "image" or visual_type == "ai_video":  # ai_video downgraded
                print(f"[AssetOrchestrator] Scene {idx}: image → fetching from ImageFetcher...")
                # For overlay kinetic_text we also need an image
                queries = [
                    f"{image_cue} cinematic 4k",
                    f"{image_cue} space astronomy",
                ]
                paths = self.image_fetcher.fetch_multi_images(
                    queries,
                    base_filename=f"job_{job_id}_scene{idx}",
                    topic_context=topic,
                )
                if paths:
                    scene_entry["asset_type"] = "image"
                    scene_entry["asset_path"] = paths[0]
                else:
                    scene_entry["asset_type"] = "none"
                    scene_entry["asset_path"] = None

            elif visual_type == "kinetic_text":
                # If kinetic_text has an image_cue AND kinetic_overlay is True,
                # fetch a base image to composite the text on top of.
                if kinetic_overlay and image_cue:
                    print(f"[AssetOrchestrator] Scene {idx}: kinetic_text (overlay) → "
                          f"fetching base image...")
                    queries = [f"{image_cue} cinematic 4k", f"{image_cue} space"]
                    paths = self.image_fetcher.fetch_multi_images(
                        queries,
                        base_filename=f"job_{job_id}_scene{idx}_base",
                        topic_context=topic,
                    )
                    scene_entry["asset_type"] = "kinetic_text_overlay"
                    scene_entry["asset_path"] = paths[0] if paths else None
                else:
                    print(f"[AssetOrchestrator] Scene {idx}: kinetic_text (full-screen) → "
                          f"no asset needed.")
                    scene_entry["asset_type"] = "kinetic_text"
                    scene_entry["asset_path"] = None

            manifest["scenes"].append(scene_entry)
            self._save_manifest(manifest)

        print(f"[AssetOrchestrator] Job {job_id} complete. "
              f"{ai_video_count} AI video clip(s), "
              f"{sum(1 for s in manifest['scenes'] if s['asset_type']=='image')} image(s), "
              f"{sum(1 for s in manifest['scenes'] if 'kinetic' in s['asset_type'])} kinetic slide(s).")
        return manifest

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
