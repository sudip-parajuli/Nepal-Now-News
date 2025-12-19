from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, concatenate_videoclips
import os

class VideoLongGenerator:
    def __init__(self, size=(1920, 1080)):
        self.size = size

    def create_daily_summary(self, sections: list, audio_path: str, output_path: str):
        """
        Creates a long-form video for daily summaries with dynamic backgrounds.
        """
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        section_duration = total_duration / len(sections) if sections else 0
        
        clips = []
        for i, section in enumerate(sections):
            if section.get('image_path') and os.path.exists(section['image_path']):
                bg = ImageClip(section['image_path']).set_duration(section_duration)
                # Resize and crop to fill 16:9 screen
                w, h = bg.size
                aspect_ratio = w/h
                target_ratio = self.size[0]/self.size[1]
                
                if aspect_ratio > target_ratio:
                    bg = bg.resize(height=self.size[1])
                else:
                    bg = bg.resize(width=self.size[0])
                
                bg = bg.set_position('center')
                # Zoom effect
                bg = bg.resize(lambda t: 1 + 0.05 * t/section_duration)
            else:
                bg = ColorClip(size=self.size, color=(20, 20, 60), duration=section_duration)
            
            try:
                # Add a semi-transparent black background to text for readability
                txt = TextClip(
                    section['text'], 
                    fontsize=50, 
                    color='white', 
                    font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold', 
                    method='caption', 
                    size=(self.size[0]-200, None),
                    bg_color='black',
                    align='Center'
                ).set_duration(section_duration).set_position(('center', 850))
                
                clips.append(CompositeVideoClip([bg, txt], size=self.size))
            except:
                clips.append(bg)

        if not clips: return

        final_video = concatenate_videoclips(clips, method="compose")
        
        # Audio Mixing (Randomized from music/ folder)
        import glob
        import random
        # Detection: Check multiple possible locations for music
        possible_music_paths = [
            "music",
            os.path.join(os.getcwd(), "music"),
            "international_news_automation/music",
            os.path.join(os.getcwd(), "..", "music")
        ]
        
        music_dir = None
        for p in possible_music_paths:
            if os.path.exists(p) and glob.glob(os.path.join(p, "*.*")):
                music_dir = p
                break
            
        music_files = []
        if music_dir:
            music_files = glob.glob(os.path.join(music_dir, "*.mp3")) + glob.glob(os.path.join(music_dir, "*.wav"))
        
        if music_files:
            try:
                bg_music_path = random.choice(music_files)
                print(f"Mixing music (long video): {bg_music_path}")
                from moviepy.audio.AudioClip import CompositeAudioClip
                from moviepy.editor import afx
                bg_music = AudioFileClip(bg_music_path).volumex(0.1).set_duration(total_duration)
                if bg_music.duration < total_duration:
                    bg_music = bg_music.fx(afx.audio_loop, duration=total_duration)
                final_audio = CompositeAudioClip([audio.volumex(1.1), bg_music])
            except Exception as e:
                print(f"Failed to load background music: {e}")
                final_audio = audio
        else:
            print(f"CRITICAL: No background music files found in any of {possible_music_paths}")
            final_audio = audio

        final_video = final_video.set_audio(final_audio)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4)
        print(f"Enhanced daily summary video saved to {output_path}")

if __name__ == "__main__":
    pass
    # vgen = VideoLongGenerator()
    # sections = [{'text': 'Story 1 summary', 'image_path': None}, {'text': 'Story 2 summary', 'image_path': None}]
    # vgen.create_daily_summary(sections, "test_audio.mp3", "test_long.mp4")
