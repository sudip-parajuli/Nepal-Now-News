import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save

class ElevenLabsTTS:
    def __init__(self, voice_id=None):
        self.api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVENLAB_API_KEY")
        if not self.api_key:
            print("WARNING: ELEVENLABS_API_KEY not found in environment variables.")
        
        self.client = None
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
            except Exception as e:
                print(f"Failed to initialize ElevenLabs client: {e}")

        # Use passed voice_id, or env var, or default "Rachel"
        self.voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "21m00Tcm4TlvDq8ikWAM"
        self.model = "eleven_multilingual_v2" 

    def generate_audio(self, text: str, output_path: str):
        """
        Generates audio for the given text using ElevenLabs API.
        Returns: output_path
        """
        if not self.api_key:
            print("Error: No ElevenLabs API Key.")
            return None

        try:
            # Use V1 SDK method: text_to_speech.convert
            # Returns a generator of bytes
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model
            )
            
            # Save the audio manually to avoid dependency on 'save' utility
            with open(output_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            return output_path
        except Exception as e:
            print(f"ElevenLabs Generation Error: {e}")
            return None
