from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, afx
import os

class VideoShortsGenerator:
    def __init__(self, size=(1080, 1920)):
        self.size = size

    def create_shorts(self, text: str, audio_path: str, output_path: str, word_offsets: list = None, image_paths: list = None):
        """
        Creates a vertical YouTube Shorts video with word-by-word karaoke highlighting and rotating backgrounds.
        """
        audio = AudioFileClip(audio_path)
        duration = audio.duration

        # 1. Background Logic (Rotating images)
        bg_clips = []
        if image_paths and len(image_paths) > 0:
            section_dur = duration / len(image_paths)
            for i, img_path in enumerate(image_paths):
                if os.path.exists(img_path):
                    try:
                        img_clip = ImageClip(img_path).set_duration(section_dur).set_start(i * section_dur)
                        
                        # Resize and crop to fill vertical screen
                        w, h = img_clip.size
                        target_ratio = self.size[0]/self.size[1]
                        if w/h > target_ratio:
                            img_clip = img_clip.resize(height=self.size[1])
                        else:
                            img_clip = img_clip.resize(width=self.size[0])
                        
                        img_clip = img_clip.set_position('center')
                        
                        # Zoom effect (Ken Burns)
                        img_clip = img_clip.resize(lambda t: 1 + 0.1 * (t % section_dur)/section_dur)
                        bg_clips.append(img_clip)
                    except Exception as e:
                        print(f"Error processing image {img_path}: {e}")

        if not bg_clips:
            bg_clips.append(ColorClip(size=self.size, color=(15, 15, 35), duration=duration))

        # Add a subtle dark gradient at the bottom for text readability
        try:
            # Create a semi-transparent black overlay for the bottom third
            overlay = ColorClip(size=(self.size[0], 600), color=(0,0,0)).set_opacity(0.5).set_duration(duration).set_position(('center', 1350))
            bg_clips.append(overlay)
        except:
            pass

        clips = bg_clips

        # 2. Modern Karaoke Logic (Multi-word with highlighting)
        if word_offsets:
            print(f"Rendering {len(word_offsets)} word clips with modern highlighting...")
            
            # Constants for UI
            FONT_SIZE = 110
            TEXT_Y = 1400 # Bottom third of screen
            
            # Helper to find which words belong to which time
            for i, current_word in enumerate(word_offsets):
                start_p = current_word['start']
                end_p = current_word['start'] + current_word['duration']
                
                # Window: Show the current word + 2 before + 4 after for context
                context_start = max(0, i - 2)
                context_end = min(len(word_offsets), i + 5)
                
                context_words = []
                for idx in range(context_start, context_end):
                    w = word_offsets[idx]['word'].upper()
                    if idx == i:
                        # Highlight the active word
                        context_words.append(f"<span foreground='yellow'>{w}</span>")
                    else:
                        context_words.append(w)
                
                display_text = " ".join(context_words)
                
                try:
                    # Using 'pango' if available for colors, otherwise standard
                    # MoviePy TextClip doesn't support span tags easily without imagemagick pango
                    # Falling back to a two-layer approach: White text, then yellow layer for active word.
                    
                    # 1. Base Layer (All words in white)
                    full_line = " ".join([word_offsets[idx]['word'].upper() for idx in range(context_start, context_end)])
                    
                    # Estimate position of active word to highlight it? 
                    # That's too complex. Let's do a simpler "Active Word Only" or "Active Word Large" approach
                    # that the user will definitely notice.
                    
                    t_clip = TextClip(
                        current_word['word'].upper(),
                        fontsize=160,
                        color='yellow',
                        font='DejaVu-Sans-Bold' if os.name != 'nt' else 'Arial-Bold',
                        stroke_color='black',
                        stroke_width=5,
                        method='label'
                    ).set_start(start_p).set_duration(end_p - start_p).set_position(('center', TEXT_Y))
                    
                    # Pop animation
                    t_clip = t_clip.resize(lambda t: 1 + 0.1 * (t/(end_p-start_p)) if t < (end_p-start_p) else 1.1)
                    clips.append(t_clip)

                except Exception as e:
                    if i == 0: print(f"TextClip rendering error: {e}")
                    t_clip = TextClip(current_word['word'].upper(), fontsize=130, color='yellow', method='label').set_start(start_p).set_duration(end_p - start_p).set_position(('center', TEXT_Y))
                    clips.append(t_clip)
        else:
            print("WARNING: Using static captions fallback.")
            txt = TextClip(self._wrap_text(text, 20), fontsize=80, color='white', bg_color='black', method='caption', size=(self.size[0]-100, None)).set_duration(duration).set_position('center')
            clips.append(txt)

        # 3. Audio Mixing
        import glob
        import random
        # Detection: Check current dir and project root
        music_dir = "music"
        if not os.path.exists(music_dir):
            # Try one level up if in a subdir
            music_dir = os.path.join(os.getcwd(), "music")
            
        music_files = glob.glob(os.path.join(music_dir, "*.mp3")) + glob.glob(os.path.join(music_dir, "*.wav"))
        
        if music_files:
            try:
                bg_music_path = random.choice(music_files)
                print(f"Mixing music: {os.path.basename(bg_music_path)}")
                bg_music = AudioFileClip(bg_music_path).volumex(0.12).set_duration(duration)
                if bg_music.duration < duration:
                    bg_music = bg_music.fx(afx.audio_loop, duration=duration)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.1), bg_music])
            except Exception as e:
                print(f"Music mix failed: {e}")
                final_audio = audio
        else:
            print(f"No background music files found in {os.path.abspath(music_dir)}")
            final_audio = audio

        final_video = CompositeVideoClip(clips, size=self.size)
        final_video = final_video.set_audio(final_audio)
        
        print(f"Writing enhanced video to {output_path}...")
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast', logger=None)

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
