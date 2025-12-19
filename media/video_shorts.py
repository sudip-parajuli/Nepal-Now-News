from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip
import os

class VideoShortsGenerator:
    def __init__(self, size=(1080, 1920)):
        self.size = size

    def create_shorts(self, text: str, audio_path: str, output_path: str):
        """
        Creates a vertical YouTube Shorts video with animated subtitles.
        """
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # Background: Dark blue gradient or solid color
        bg = ColorClip(size=self.size, color=(10, 10, 40), duration=duration)

        # Simple centered text (in a real scenario, we'd split text by time)
        # For MVP, we'll display the headline or the whole script in chunks
        text_lines = self._wrap_text(text, 20)
        clips = [bg]
        
        # Use wrapped text to avoid ImageMagick width/height issues
        wrapped_text = self._wrap_text(text, 25)
        
        # Try a common font, or let MoviePy pick default
        try:
            txt_clip = TextClip(
                wrapped_text, 
                fontsize=70, 
                color='white', 
                font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold', 
                method='label', 
                align='Center'
            ).set_duration(duration).set_position('center')
        except:
            txt_clip = TextClip(
                wrapped_text, 
                fontsize=70, 
                color='white', 
                method='label', 
                align='Center'
            ).set_duration(duration).set_position('center')

        final_video = CompositeVideoClip([bg, txt_clip])
        final_video = final_video.set_audio(audio)
        
        # Write file with low bitrate for speed
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"Video saved to {output_path}")

    def _wrap_text(self, text: str, width: int) -> str:
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            if len(" ".join(current_line + [word])) <= width:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
        lines.append(" ".join(current_line))
        return "\n".join(lines)

if __name__ == "__main__":
    pass
    # Test generation (Requires ImageMagick configured for MoviePy)
    # vgen = VideoShortsGenerator()
    # vgen.create_shorts("BREAKING NEWS: A major international event is unfolding right now. More updates to follow.", "test_narration.mp3", "test_video.mp4")
