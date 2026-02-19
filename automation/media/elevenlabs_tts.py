import os
import sys

class ElevenLabsTTS:
    def __init__(self, voice_id=None):
        self.api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVENLAB_API_KEY")
        if not self.api_key:
            print("WARNING: ELEVENLABS_API_KEY not found in environment variables.")
        
        self.client = None
        # Use passed voice_id, or env var, or default "Rachel"
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
        self.model = "eleven_multilingual_v2" 

        if self.api_key:
            try:
                # Try V1/V2+ SDK Client
                from elevenlabs.client import ElevenLabs
                self.client = ElevenLabs(api_key=self.api_key)
                print("DEBUG: Initialized ElevenLabs V1/V2 Client.")
            except ImportError:
                print("DEBUG: ElevenLabs.client not found, using legacy functional API if possible.")
                self.client = None
            except Exception as e:
                print(f"Failed to initialize ElevenLabs client: {e}")

    def generate_audio(self, text: str, output_path: str):
        """
        Generates audio for the given text using ElevenLabs.
        Attempts both client-based and functional APIs.
        """
        if not self.api_key:
            print("Error: No ElevenLabs API Key.")
            return None

        print(f"DEBUG: ElevenLabsTTS.generate_audio starting... (File: {__file__})")

        # TRY CLIENT API (V1/V2)
        if self.client:
            try:
                print("DEBUG: Trying client.text_to_speech.convert...")
                audio_generator = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=self.voice_id,
                    model_id=self.model
                )
                with open(output_path, "wb") as f:
                    for chunk in audio_generator:
                        f.write(chunk)
                return output_path
            except AttributeError:
                print("DEBUG: client.text_to_speech.convert missing. Trying client.generate...")
                try:
                    audio_generator = self.client.generate(
                        text=text,
                        voice_id=self.voice_id,
                        model_id=self.model
                    )
                    # For v1 client.generate, it return bytes? Or a generator?
                    # In some V1 previews it returns bytes.
                    if isinstance(audio_generator, bytes):
                        with open(output_path, "wb") as f: f.write(audio_generator)
                    else:
                        with open(output_path, "wb") as f:
                            for chunk in audio_generator: f.write(chunk)
                    return output_path
                except Exception as e2:
                    print(f"DEBUG: client.generate failed: {e2}")
            except Exception as e:
                print(f"DEBUG: client.text_to_speech.convert failed: {e}")

        # TRY FUNCTIONAL API (Legacy/0.x or simplified 1.x)
        try:
            print("DEBUG: Trying functional API: elevenlabs.generate...")
            import elevenlabs
            # Set key globally for functional API
            elevenlabs.set_api_key(self.api_key)
            audio = elevenlabs.generate(
                text=text,
                voice=self.voice_id,
                model=self.model
            )
            # In 0.x/stable 1.x functional API, generate returns bytes
            if hasattr(elevenlabs, 'save'):
                elevenlabs.save(audio, output_path)
            else:
                with open(output_path, "wb") as f:
                    f.write(audio)
            return output_path
        except Exception as e:
            print(f"DEBUG: All ElevenLabs methods failed. Final error: {e}")
            if self.client:
                try: print(f"DEBUG: Client attributes: {dir(self.client)[:20]}")
                except: pass
            return None
