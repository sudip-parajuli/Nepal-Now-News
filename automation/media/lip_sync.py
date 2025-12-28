import os
import subprocess
import requests
import time
from typing import Optional

class LipSyncEngine:
    def __init__(self, wav2lip_dir=None, checkpoint_path=None):
        self.wav2lip_dir = wav2lip_dir or os.getenv("WAV2LIP_DIR", "Wav2Lip")
        self.checkpoint_path = checkpoint_path or os.getenv("WAV2LIP_CHECKPOINT", os.path.join(self.wav2lip_dir, "checkpoints/wav2lip_gan.pth"))
        self.repo_url = "https://github.com/Rudrabha/Wav2Lip.git"
        
        # Reliable GAN checkpoint from HuggingFace (Alternative public source)
        self.model_url = "https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth"
        
        # Face Detector Model
        self.detector_url = "https://huggingface.co/rippertnt/wav2lip/resolve/main/s3fd.pth"
        self.detector_path = os.path.join(self.wav2lip_dir, "face_detection/detection/sfd/s3fd.pth")
        
        import sys
        self.python_exe = sys.executable or "python"

    async def sync(self, face_path: str, audio_path: str, output_path: str) -> str:
        """
        Runs Wav2Lip inference. Auto-sets up dependencies if missing.
        """
        if not os.path.exists(face_path):
            print(f"ERROR: Face asset not found: {face_path}")
            return self._create_static_fallback(face_path, audio_path, output_path)

        try:
            self._ensure_setup()
            # Ensure Wav2Lip 'temp' directory exists (critical for intermediate FFmpeg files)
            os.makedirs("temp", exist_ok=True)
        except Exception as e:
            print(f"Setup failed: {e}. Falling back to static.")
            return self._create_static_fallback(face_path, audio_path, output_path)

        # Inference logic
        inference_script = os.path.join(self.wav2lip_dir, "inference.py")
        
        # CPU-optimized command (mostly default, but ensure it uses CPU if no GPU)
        cmd = [
            self.python_exe, inference_script,
            "--checkpoint_path", self.checkpoint_path,
            "--face", face_path,
            "--audio", audio_path,
            "--outfile", output_path,
            "--nosmooth" # Faster on CPU
        ]
        
        print(f"Executing Wav2Lip Sync: {os.path.basename(face_path)} + {os.path.basename(audio_path)}")
        start_time = time.time()
        
        try:
            # Set PYTHONPATH so inference.py can find its own modules
            env = os.environ.copy()
            env["PYTHONPATH"] = os.path.abspath(self.wav2lip_dir)
            
            # Increased timeout for CPU-bound task in CI
            process = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
            
            if process.returncode == 0 and os.path.exists(output_path):
                elapsed = time.time() - start_time
                print(f"Lip-sync completed in {elapsed:.2f}s")
                return output_path
            else:
                print(f"Wav2Lip Error (Code {process.returncode}): {process.stderr}")
                print(f"STDOUT: {process.stdout}")
        except subprocess.TimeoutExpired:
            print("Wav2Lip inference timed out (15 min limit).")
        except Exception as e:
            print(f"Inference error: {e}")

        return self._create_static_fallback(face_path, audio_path, output_path)

    def _ensure_setup(self):
        """Checks for repo and model, downloads if necessary."""
        # 1. Clone Repo
        inference_script = os.path.join(self.wav2lip_dir, "inference.py")
        if not os.path.exists(inference_script):
            if os.path.exists(self.wav2lip_dir):
                # If directory exists but script is missing, it might be a partial clone or cache
                print(f"Wav2Lip directory exists but inference.py is missing. Re-cloning...")
                import shutil
                try:
                    shutil.rmtree(self.wav2lip_dir)
                except Exception as e:
                    print(f"Warning: Could not remove existing Wav2Lip dir: {e}")
            
            print(f"Cloning Wav2Lip repository from {self.repo_url}...")
            subprocess.run(["git", "clone", self.repo_url, self.wav2lip_dir], check=True)
        
        # 2. Download Model Weights
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        self._download_if_missing(self.model_url, self.checkpoint_path, "Wav2Lip GAN")
        
        # 3. Download Face Detector (S3FD)
        os.makedirs(os.path.dirname(self.detector_path), exist_ok=True)
        self._download_if_missing(self.detector_url, self.detector_path, "Face Detector (S3FD)")

    def _download_if_missing(self, url: str, path: str, name: str):
        if not os.path.exists(path) or os.path.getsize(path) < 1000000: # < 1MB check
            print(f"Downloading {name} model weights...")
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            r = requests.get(url, stream=True, timeout=120, headers=headers, allow_redirects=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"{name} weights downloaded successfully.")
            else:
                raise Exception(f"Failed to download {name}. Status: {r.status_code}")

    def _create_static_fallback(self, face_path: str, audio_path: str, output_path: str) -> str:
        from moviepy.editor import ImageClip, AudioFileClip
        print("Falling back to static AI Anchor video (Full Screen requested)...")
        try:
            audio = AudioFileClip(audio_path)
            clip = ImageClip(face_path).set_duration(audio.duration).set_audio(audio)
            # Match the requested full-screen height (1920 for shorts)
            clip = clip.resize(height=1920) 
            clip.write_videofile(output_path, fps=12, codec="libx264", audio_codec="aac", logger=None, preset='ultrafast')
            return output_path
        except Exception as e:
            print(f"Fallback generation failed: {e}")
            return ""
