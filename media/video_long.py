from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, concatenate_videoclips
import os

class VideoLongGenerator:
    def __init__(self, size=(1920, 1080)):
        self.size = size

    def create_daily_summary(self, sections: list, audio_path: str, output_path: str):
        """
        Creates a long-form video for daily summaries.
        sections: list of dicts with {'text': ..., 'image_path': ...}
        """
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        
        # For simplicity, we'll divide duration equally among sections
        # In a real app, we'd use timestamps from the script.
        section_duration = total_duration / len(sections)
        
        clips = []
        for i, section in enumerate(sections):
            # Fallback to color if image missing
            if section.get('image_path') and os.path.exists(section['image_path']):
                bg = ImageClip(section['image_path']).set_duration(section_duration).resize(height=self.size[1])
                if bg.w < self.size[0]:
                    bg = bg.margin(left=(self.size[0]-bg.w)//2, color=(0,0,0))
            else:
                bg = ColorClip(size=self.size, color=(20, 20, 60), duration=section_duration)
            
            try:
                txt = TextClip(
                    section['text'], 
                    fontsize=50, 
                    color='white', 
                    font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold', 
                    method='label', 
                    bg_color='black',
                    align='Center'
                ).set_duration(section_duration).set_position('bottom')
            except:
                txt = TextClip(
                    section['text'], 
                    fontsize=50, 
                    color='white', 
                    method='label', 
                    bg_color='black',
                    align='Center'
                ).set_duration(section_duration).set_position('bottom')
            
            clips.append(CompositeVideoClip([bg, txt]))

        final_video = concatenate_videoclips(clips)
        final_video = final_video.set_audio(audio)
        
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        print(f"Daily summary video saved to {output_path}")

if __name__ == "__main__":
    pass
    # vgen = VideoLongGenerator()
    # sections = [{'text': 'Story 1 summary', 'image_path': None}, {'text': 'Story 2 summary', 'image_path': None}]
    # vgen.create_daily_summary(sections, "test_audio.mp3", "test_long.mp4")
