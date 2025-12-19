from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, afx
import os

class VideoShortsGenerator:
    def __init__(self, size=(1080, 1920)):
        self.size = size

    def create_shorts(self, text: str, audio_path: str, output_path: str, word_offsets: list = None, image_path: str = None):
        """
        Creates a vertical YouTube Shorts video with word-by-word karaoke highlighting.
        """
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # 1. Background Logic
        if image_path and os.path.exists(image_path):
            bg = ImageClip(image_path).set_duration(duration)
            # Resize and crop to fill vertical screen (1080x1920)
            w, h = bg.size
            aspect_ratio = w/h
            target_ratio = self.size[0]/self.size[1]
            
            if aspect_ratio > target_ratio:
                bg = bg.resize(height=self.size[1])
            else:
                bg = bg.resize(width=self.size[0])
            
            bg = bg.set_position('center')
            # Ken Burns effect: subtle zoom
            bg = bg.resize(lambda t: 1 + 0.1 * t/duration)
        else:
            bg = ColorClip(size=self.size, color=(15, 15, 35), duration=duration)

        clips = [bg]

        # 2. Advanced Karaoke Logic (Highlighted Word)
        if word_offsets:
            # We'll display 1-3 words at a time in the center
            group_size = 3
            for i in range(len(word_offsets)):
                # Get the window of words to show (e.g., current word and next 2)
                window = word_offsets[max(0, i-1):i+2]
                if not window: continue
                
                current_word = word_offsets[i]
                start_p = current_word['start']
                end_p = current_word['start'] + current_word['duration']
                
                # To make it feel "karaoke", for each word's duration, 
                # we show the full sentence but highlight the active word.
                # However, for Shorts, showing 1 big word at a time is often better.
                # Let's do: Big highlighted word in the center.
                
                word_text = current_word['word'].upper()
                
                try:
                    # Drop shadow / Stroke version
                    t_clip = TextClip(
                        word_text,
                        fontsize=140,
                        color='yellow',
                        font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold',
                        stroke_color='black',
                        stroke_width=3,
                        method='label'
                    ).set_start(start_p).set_duration(end_p - start_p).set_position('center')
                    
                    # Add a subtle "pop" animation
                    t_clip = t_clip.resize(lambda t: 1 + 0.1 * (t/(end_p-start_p)) if t < (end_p-start_p) else 1.1)
                    
                    clips.append(t_clip)
                except Exception as e:
                    print(f"TextClip error: {e}")
                    t_clip = TextClip(word_text, fontsize=120, color='yellow', method='label').set_start(start_p).set_duration(end_p - start_p).set_position('center')
                    clips.append(t_clip)
        else:
            # Fallback
            txt = TextClip(self._wrap_text(text, 20), fontsize=80, color='white', method='label').set_duration(duration).set_position('center')
            clips.append(txt)

        # 3. Audio Mixing (Randomized from music/ folder)
        import glob
        import random
        music_files = glob.glob("music/*.mp3") + glob.glob("music/*.wav")
        if music_files:
            try:
                bg_music_path = random.choice(music_files)
                print(f"Using random background music: {bg_music_path}")
                bg_music = AudioFileClip(bg_music_path).volumex(0.15).set_duration(duration)
                if bg_music.duration < duration:
                    bg_music = bg_music.fx(afx.audio_loop, duration=duration)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.2), bg_music])
            except Exception as e:
                print(f"Failed to load background music: {e}")
                final_audio = audio
        else:
            final_audio = audio

        final_video = CompositeVideoClip(clips, size=self.size)
        final_video = final_video.set_audio(final_audio)
        
        # 4. Rendering
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast')

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
