import os
import base64
import requests


class HumeTTS:
    """
    Hume AI Octave TTS integration (free tier).
    Uses the REST API directly for maximum version compatibility.
    Produces expressive, human-sounding voice output.
    """

    BASE_URL = "https://api.hume.ai/v0/tts"

    def __init__(self, voice_id: str = None):
        self.api_key = os.getenv("HUME_API_KEY")
        self.voice_id = (
            voice_id
            or os.getenv("HUME_VOICE_ID")
            or os.getenv("HUME_VOICE_ID_SCIENCE")
        )

        if not self.api_key:
            print("HumeTTS WARNING: HUME_API_KEY not set in environment.")
        if not self.voice_id:
            print("HumeTTS WARNING: No voice ID set. Using Hume default voice.")

    def generate_audio(self, text: str, output_path: str):
        """
        Generate TTS audio using Hume Octave API.
        Returns (output_path, word_offsets) on success, or (None, []) on failure.
        """
        if not self.api_key:
            print("HumeTTS: Skipping — no API key.")
            return None, []

        headers = {
            "X-Hume-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

        utterance = {"text": text}
        if self.voice_id:
            utterance["voice"] = {"id": self.voice_id}

        payload = {
            "utterances": [utterance],
            "format": {"type": "mp3"},
            "num_generations": 1,
        }

        try:
            print(f"HumeTTS: Requesting audio for: {text[:60]}...")
            resp = requests.post(
                self.BASE_URL, headers=headers, json=payload, timeout=90
            )

            if resp.status_code != 200:
                print(
                    f"HumeTTS: API error {resp.status_code} — {resp.text[:300]}"
                )
                return None, []

            data = resp.json()
            generations = data.get("generations", [])

            if not generations:
                print("HumeTTS: Empty generations list in response.")
                return None, []

            gen = generations[0]
            audio_b64 = gen.get("audio", "")

            if not audio_b64:
                print("HumeTTS: No audio field in generation.")
                return None, []

            audio_bytes = base64.b64decode(audio_b64)

            out_dir = os.path.dirname(output_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)

            with open(output_path, "wb") as f:
                f.write(audio_bytes)

            print(
                f"HumeTTS: Audio saved to {output_path} ({len(audio_bytes):,} bytes)"
            )

            word_offsets = self._extract_word_offsets(gen)
            print(f"HumeTTS: Extracted {len(word_offsets)} word timestamps.")

            return output_path, word_offsets

        except requests.exceptions.Timeout:
            print("HumeTTS: Request timed out (90s).")
        except Exception as e:
            print(f"HumeTTS: Unexpected error — {e}")

        return None, []

    def _extract_word_offsets(self, generation: dict) -> list:
        """
        Extract word-level timing from Hume generation response.
        Handles multiple known response formats gracefully.
        """
        offsets = []

        # Format 1: snippets[].timestamps (dict with begin/end)
        for snippet in generation.get("snippets", []):
            ts = snippet.get("timestamps", {})
            word = snippet.get("text", "").strip()
            if isinstance(ts, dict) and word:
                begin = float(ts.get("begin", ts.get("start", 0.0)))
                end = float(ts.get("end", begin + 0.3))
                offsets.append({"word": word, "start": begin, "duration": end - begin})
            elif isinstance(ts, list):
                for t in ts:
                    w = t.get("word", "").strip()
                    begin = float(t.get("begin", t.get("start", 0.0)))
                    end = float(t.get("end", begin + 0.3))
                    if w:
                        offsets.append({"word": w, "start": begin, "duration": end - begin})

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
