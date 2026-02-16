import os
from elevenlabs.client import ElevenLabs
from elevenlabs import save

class ElevenLabsTTS:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            print("WARNING: ELEVENLABS_API_KEY not found in environment variables.")
        self.client = ElevenLabs(api_key=self.api_key)
        # Default Nepali voice or a voice that sounds good for Nepali
        # We might need a specific Voice ID. For now, let's use a standard one or one provided by user if any.
        # User didn't specify a voice ID, so we might need to list them or use a default 'Rachel' or similar, 
        # but 'eleven_multilingual_v2' model is key for Nepali.
        # "Chris" is often good for news.
        self.voice_id = "Chris" # Placeholder, can be changed.
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
            audio = self.client.generate(
                text=text,
                voice=self.voice_id,
                model=self.model
            )
            
            # Save the audio
            save(audio, output_path)
            
            return output_path
        except Exception as e:
            print(f"ElevenLabs Generation Error: {e}")
            return None
