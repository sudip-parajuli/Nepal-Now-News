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
            transition_time = 4.0 # Change image every 4 seconds for dynamism
            for i, img_path in enumerate(image_paths):
                if os.path.exists(img_path):
                    try:
                        img_clip = ImageClip(img_path).set_duration(transition_time).set_start(i * transition_time)
                        
                        # Resize and crop to fill vertical screen
                        w, h = img_clip.size
                        target_ratio = self.size[0]/self.size[1]
                        if w/h > target_ratio:
                            img_clip = img_clip.resize(height=self.size[1])
                        else:
                            img_clip = img_clip.resize(width=self.size[0])
                        
                        img_clip = img_clip.set_position('center')
                        
                        # Ken Burns + Rapid Shift
                        img_clip = img_clip.resize(lambda t: 1.05 + 0.1 * (t / transition_time))
                        bg_clips.append(img_clip)
                    except Exception as e:
                        print(f"Error processing image {img_path}: {e}")
            
            # Loop background if shorter than audio
            if bg_clips:
                total_bg_dur = len(bg_clips) * transition_time
                if total_bg_dur < duration:
                    # Simple loop: duplicate the last clip to fill the gap or extend the last one
                    bg_clips[-1] = bg_clips[-1].set_duration(duration - bg_clips[-1].start)

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

        # 2. Modern Karaoke Logic (3-line Page-Sync with Highlight Background)
        if word_offsets:
            print(f"Rendering {len(word_offsets)} points with 3-line Page-Sync...")
            
            # UI Config
            FONT_SIZE = 80
            LINE_HEIGHT = 110
            START_Y = 1350
            MAX_CHARS_PER_LINE = 22
            HIGHLIGHT_BG = 'yellow'
            HIGHLIGHT_TEXT = 'black'
            NORMAL_TEXT = 'white'
            FONT = 'Nirmala-UI' if os.name == 'nt' else 'Noto-Sans-Devanagari'
            HIGHLIGHT_FONT = 'Nirmala-UI-Bold' if os.name == 'nt' else 'Noto-Sans-Devanagari-Bold'
            
            # Step 1: Group words into lines
            lines = []
            curr_line = []
            curr_len = 0
            for w in word_offsets:
                w_text = w['word']
                if curr_len + len(w_text) > MAX_CHARS_PER_LINE and curr_line:
                    lines.append(curr_line)
                    curr_line = []
                    curr_len = 0
                curr_line.append(w)
                curr_len += len(w_text) + 1
            if curr_line:
                lines.append(curr_line)
            
            # Step 2: Group lines into pages of 3
            pages = [lines[i:i + 3] for i in range(0, len(lines), 3)]
            
            for p_idx, page in enumerate(pages):
                page_start = page[0][0]['start']
                page_end = page[-1][-1]['start'] + page[-1][-1]['duration']
                
                # Render each line in the page
                for l_idx, line in enumerate(page):
                    y_pos = START_Y + (l_idx * LINE_HEIGHT)
                    line_text = " ".join([w['word'] for w in line]).upper()
                    
                    try:
                        # 1. Base Line (Dimmed White for Context)
                        base_txt = TextClip(
                            line_text,
                            fontsize=FONT_SIZE,
                            color=NORMAL_TEXT,
                            font=FONT,
                            stroke_color='black',
                            stroke_width=2,
                            method='label'
                        ).set_start(page_start).set_duration(page_end - page_start).set_position(('center', y_pos)).set_opacity(0.6)
                        clips.append(base_txt)
                        
                        # 2. Calculate Word Positions for Highlighting
                        # We need the alignment to match the centered 'base_txt'
                        line_width = base_txt.size[0]
                        current_x = (self.size[0] - line_width) // 2
                        
                        for w_info in line:
                            w_text = w_info['word'].upper()
                            # Measure word width (including space) to increment current_x
                            # Note: We use a space suffix for accurate spacing measurement
                            w_full = w_text + " "
                            temp_w = TextClip(w_full, fontsize=FONT_SIZE, font=FONT, method='label')
                            w_width = temp_w.size[0]
                            temp_w.close()
                            
                            # 3. Active Highlight Clip (Background Shape + Color)
                            highlight = TextClip(
                                w_text,
                                fontsize=FONT_SIZE,
                                color=HIGHLIGHT_TEXT,
                                bg_color=HIGHLIGHT_BG,
                                font=HIGHLIGHT_FONT,
                                method='label'
                            ).set_start(w_info['start']).set_duration(w_info['duration']).set_position((current_x, y_pos))
                            
                            clips.append(highlight)
                            # Increment for next word in the line
                            current_x += w_width
                            
                    except Exception as e:
                        if p_idx == 0: print(f"Caption rendering error: {e}")
                        continue
        else:
            print("WARNING: Falling back to block captions.")
            txt = TextClip(
                self._wrap_text(text, 25), 
                fontsize=70, 
                color='white', 
                bg_color='black', 
                font='Noto-Sans-Devanagari' if os.name != 'nt' else 'Nirmala-UI',
                method='caption', 
                size=(self.size[0]-100, None)
            ).set_duration(duration).set_position('center')
            clips.append(txt)

        # 3. Audio Mixing
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
                print(f"Mixing music: {bg_music_path}")
                bg_music = AudioFileClip(bg_music_path).volumex(0.12).set_duration(duration)
                if bg_music.duration < duration:
                    bg_music = bg_music.fx(afx.audio_loop, duration=duration)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.1), bg_music])
            except Exception as e:
                print(f"Music mix failed: {e}")
                final_audio = audio
        else:
            print(f"CRITICAL: No background music files found in any of {possible_music_paths}")
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
