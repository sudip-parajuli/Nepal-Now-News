import os
import base64
import requests


class HumeTTS:
    """
    Hume AI Octave TTS integration (free tier).
    - Rotates up to 6 API keys (HUME_API_KEY, HUME_API_KEY1..HUME_API_KEY5)
      automatically when a key hits its quota/rate limit.
    - Randomly picks from available voice IDs (HUME_VOICE_ID, HUME_VOICE_ID_1)
      each call for natural variety.
    """

    BASE_URL = "https://api.hume.ai/v0/tts"

    def __init__(self, voice_id: str = None):
        import random
        self._random = random

        # Collect all available API keys in priority order
        self.api_keys = []
        for env_name in [
            "HUME_API_KEY",
            "HUME_API_KEY2",
            "HUME_API_KEY3",
            "HUME_API_KEY4",
            "HUME_API_KEY5",
        ]:
            val = os.getenv(env_name, "").strip()
            if val:
                self.api_keys.append(val)

        # Collect all available voice IDs
        self.voice_ids = []
        if voice_id:
            self.voice_ids.append(voice_id)
        for env_name in ["HUME_VOICE_ID", "HUME_VOICE_ID_1"]:
            val = os.getenv(env_name, "").strip()
            if val and val not in self.voice_ids:
                self.voice_ids.append(val)

        if not self.api_keys:
            print("HumeTTS WARNING: No HUME_API_KEY* found in environment.")
        else:
            print(f"HumeTTS: {len(self.api_keys)} API key(s) and {len(self.voice_ids)} voice ID(s) available.")

    def generate_audio(self, text: str, output_path: str):
        """
        Generate TTS audio using Hume Octave API.
        Rotates through all available API keys on quota/rate-limit errors.
        Returns (output_path, word_offsets) on success, or (None, []) on failure.
        """
        if not self.api_keys:
            print("HumeTTS: Skipping — no API keys available.")
            return None, []

        # Pick a random voice ID for this call (variety + rotation)
        chosen_voice = self._random.choice(self.voice_ids) if self.voice_ids else None
        if chosen_voice:
            print(f"HumeTTS: Using voice ID: {chosen_voice[:8]}...")

        utterance = {"text": text}
        if chosen_voice:
            utterance["voice"] = {"id": chosen_voice}

        payload = {
            "utterances": [utterance],
            "format": {"type": "mp3"},
            "num_generations": 1,
        }

        # Try each key in sequence
        for attempt, api_key in enumerate(self.api_keys, start=1):
            key_preview = f"{api_key[:6]}...{api_key[-4:]}"
            print(f"HumeTTS: Attempting key {attempt}/{len(self.api_keys)} ({key_preview}) ...")

            headers = {
                "X-Hume-Api-Key": api_key,
                "Content-Type": "application/json",
            }

            try:
                resp = requests.post(
                    self.BASE_URL, headers=headers, json=payload, timeout=90
                )

                # Quota / auth errors — rotate to next key
                if resp.status_code in (401, 402, 403, 429):
                    print(
                        f"HumeTTS: Key {attempt} returned {resp.status_code} "
                        f"({resp.text[:120]}). Trying next key..."
                    )
                    continue

                if resp.status_code != 200:
                    print(f"HumeTTS: Key {attempt} API error {resp.status_code}: {resp.text[:200]}")
                    continue

                data = resp.json()
                generations = data.get("generations", [])
                if not generations:
                    print(f"HumeTTS: Key {attempt} — empty generations list.")
                    continue

                gen = generations[0]
                audio_b64 = gen.get("audio", "")
                if not audio_b64:
                    print(f"HumeTTS: Key {attempt} — no audio field.")
                    continue

                audio_bytes = base64.b64decode(audio_b64)

                out_dir = os.path.dirname(output_path)
                if out_dir:
                    os.makedirs(out_dir, exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(audio_bytes)

                print(
                    f"HumeTTS: ✓ Key {attempt} succeeded — "
                    f"{len(audio_bytes):,} bytes → {output_path}"
                )

                word_offsets = self._extract_word_offsets(gen)
                print(f"HumeTTS: Extracted {len(word_offsets)} word timestamps.")
                return output_path, word_offsets

            except requests.exceptions.Timeout:
                print(f"HumeTTS: Key {attempt} timed out (90 s). Trying next key...")
            except Exception as e:
                print(f"HumeTTS: Key {attempt} unexpected error — {e}. Trying next key...")

        print("HumeTTS: All API keys exhausted — falling back to next TTS engine.")
        return None, []

    def _extract_word_offsets(self, generation: dict) -> list:
        """
        Extract word-level timing from Hume generation response.
        Handles multiple known response formats gracefully.
        """
        offsets = []

        # Format 1: snippets[].timestamps (dict with begin/end)
        for snippet in generation.get("snippets", []):
            if not isinstance(snippet, dict):
                continue
            ts = snippet.get("timestamps", {})
            word = snippet.get("text", "").strip()
            if isinstance(ts, dict) and word:
                try:
                    # In some API versions ts['begin'] is a list of floats
                    b_val = ts.get("begin", ts.get("start", 0.0))
                    begin = float(b_val[0]) if isinstance(b_val, list) else float(b_val)
                    e_val = ts.get("end", begin + 0.3)
                    end = float(e_val[-1]) if isinstance(e_val, list) else float(e_val)
                    offsets.append({"word": word, "start": begin, "duration": end - begin})
                except Exception:
                    pass
            elif isinstance(ts, list):
                for t in ts:
                    if not isinstance(t, dict):
                        continue
                    w = t.get("word", "").strip()
                    try:
                        b_val = t.get("begin", t.get("start", 0.0))
                        begin = float(b_val[0]) if isinstance(b_val, list) else float(b_val)
                        e_val = t.get("end", begin + 0.3)
                        end = float(e_val[-1]) if isinstance(e_val, list) else float(e_val)
                        if w:
                            offsets.append({"word": w, "start": begin, "duration": end - begin})
                    except Exception:
                        pass

        if offsets:
            return offsets

        # Format 2: word_timestamps[] (alternative)
        for wt in generation.get("word_timestamps", []):
            word = wt.get("word", "").strip()
            begin = float(wt.get("begin", wt.get("start", 0.0)))
            end = float(wt.get("end", begin + 0.3))
            if word:
                offsets.append({"word": word, "start": begin, "duration": end - begin})

        return offsets
