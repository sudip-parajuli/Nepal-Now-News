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
        # Reliable GAN checkpoint from HuggingFace
        self.model_url = "https://huggingface.co/KalidX/Wav2Lip/resolve/main/wav2lip_gan.pth"
        self.python_exe = "python"

    async def sync(self, face_path: str, audio_path: str, output_path: str) -> str:
        """
        Runs Wav2Lip inference. Auto-sets up dependencies if missing.
        """
        if not os.path.exists(face_path):
            print(f"ERROR: Face asset not found: {face_path}")
            return self._create_static_fallback(face_path, audio_path, output_path)

        try:
            self._ensure_setup()
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
        except subprocess.TimeoutExpired:
            print("Wav2Lip inference timed out (15 min limit).")
        except Exception as e:
            print(f"Inference error: {e}")

        return self._create_static_fallback(face_path, audio_path, output_path)

    def _ensure_setup(self):
        """Checks for repo and model, downloads if necessary."""
        # 1. Clone Repo
        if not os.path.exists(self.wav2lip_dir):
            print(f"Cloning Wav2Lip repository from {self.repo_url}...")
            subprocess.run(["git", "clone", self.repo_url, self.wav2lip_dir], check=True)
            
            # Patch for some common Wav2Lip attribute errors in newer python/libs if needed
            # (Usually not needed for basic inference)
        
        # 2. Download Model Weights
        os.makedirs(os.path.dirname(self.checkpoint_path), exist_ok=True)
        if not os.path.exists(self.checkpoint_path) or os.path.getsize(self.checkpoint_path) < 100000000: # < 100MB check
            print(f"Downloading Wav2Lip GAN model weights (This might take a minute)...")
            r = requests.get(self.model_url, stream=True, timeout=60)
            if r.status_code == 200:
                with open(self.checkpoint_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print("Model weights downloaded successfully.")
            else:
                raise Exception(f"Failed to download model weights. Status: {r.status_code}")

    def _create_static_fallback(self, face_path: str, audio_path: str, output_path: str) -> str:
        from moviepy.editor import ImageClip, AudioFileClip
        print("Falling back to static AI Anchor video...")
        try:
            audio = AudioFileClip(audio_path)
            clip = ImageClip(face_path).set_duration(audio.duration).set_audio(audio)
            clip = clip.resize(height=1080) 
            clip.write_videofile(output_path, fps=12, codec="libx264", audio_codec="aac", logger=None, preset='ultrafast')
            return output_path
        except Exception as e:
            print(f"Fallback generation failed: {e}")
            return ""
