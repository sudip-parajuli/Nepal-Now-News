from moviepy.editor import TextClip, ColorClip, CompositeVideoClip, AudioFileClip, ImageClip, VideoFileClip, afx
import os
import glob
import random
import re

class VideoShortsGenerator:
    def __init__(self, size=(1080, 1920)):
        self.size = size

    def create_shorts(self, text: str, audio_path: str, output_path: str, word_offsets: list = None, media_paths: list = None, branding: dict = None):
        """
        media_paths can contain both image and video file paths.
        branding: dict with keys like 'accent_color', 'bg_color', 'music_volume'
        """
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        bg_clips = []
        
        # Branding defaults (Cosmic/Science style)
        accent = (branding or {}).get('accent_color', 'yellow')
        bg_overlay_color = (branding or {}).get('bg_color', (0,0,0))
        music_vol = (branding or {}).get('music_volume', 0.12)

        if media_paths and len(media_paths) > 0:
            transition_time = duration / len(media_paths) if len(media_paths) > 0 else 4.0
            transition_time = max(min(transition_time, 6.0), 3.0) 
            
            for i, m_path in enumerate(media_paths):
                if os.path.exists(m_path):
                    try:
                        is_video = m_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))
                        start_time = i * transition_time
                        
                        if is_video:
                            clip = VideoFileClip(m_path).without_audio()
                            if clip.duration < transition_time:
                                clip = clip.fx(afx.loop, duration=transition_time)
                            else:
                                clip = clip.subclip(0, transition_time)
                        else:
                            clip = ImageClip(m_path).set_duration(transition_time)

                        clip = clip.set_start(start_time)
                        
                        w, h = clip.size
                        target_ratio = self.size[0]/self.size[1]
                        if w/h > target_ratio: clip = clip.resize(height=self.size[1])
                        else: clip = clip.resize(width=self.size[0])
                        clip = clip.set_position('center')
                        
                        if not is_video:
                            clip = clip.resize(lambda t: 1.05 + 0.05 * (t / transition_time))
                            
                        bg_clips.append(clip)
                    except Exception as e:
                        print(f"Error processing media {m_path}: {e}")
            
            if bg_clips:
                actual_bg_dur = sum([c.duration for c in bg_clips])
                if actual_bg_dur < duration:
                    bg_clips[-1] = bg_clips[-1].set_duration(duration - bg_clips[-1].start)
        
        if not bg_clips:
            bg_clips.append(ColorClip(size=self.size, color=(15, 15, 35), duration=duration))
        
        try:
            overlay = ColorClip(size=(self.size[0], 600), color=bg_overlay_color).set_opacity(0.5).set_duration(duration).set_position(('center', 1350))
            bg_clips.append(overlay)
        except: pass

        clips = bg_clips
        if word_offsets:
            FONT_SIZE, LINE_HEIGHT, START_Y, MAX_CHARS_PER_LINE = 80, 110, 1350, 25 
            HIGHLIGHT_BG, HIGHLIGHT_TEXT, NORMAL_TEXT = accent, 'black', 'white'
            
            is_nepali = re.search(r'[\u0900-\u097F]', text)
            if is_nepali:
                FONT = 'Nirmala-UI' if os.name == 'nt' else 'Noto-Sans-Devanagari'
                HIGHLIGHT_FONT = 'Nirmala-UI-Bold' if os.name == 'nt' else 'Noto-Sans-Devanagari-Bold'
            else:
                FONT = 'Arial' if os.name == 'nt' else 'DejaVu-Sans'
                HIGHLIGHT_FONT = 'Arial-Bold' if os.name == 'nt' else 'DejaVu-Sans-Bold'

            lines, curr_line, curr_len = [], [], 0
            for w in word_offsets:
                if curr_len + len(w['word']) > MAX_CHARS_PER_LINE and curr_line:
                    lines.append(curr_line)
                    curr_line, curr_len = [], 0
                curr_line.append(w)
                curr_len += len(w['word']) + 1
            if curr_line: lines.append(curr_line)
            pages = [lines[i:i + 3] for i in range(0, len(lines), 3)]
            for page in pages:
                page_start, page_end = page[0][0]['start'], page[-1][-1]['start'] + page[-1][-1]['duration']
                for l_idx, line in enumerate(page):
                    y_pos = START_Y + (l_idx * LINE_HEIGHT)
                    line_text = " ".join([w['word'] for w in line]).upper()
                    try:
                        # Render full line base in white using 'caption' for robustness
                        base_txt = TextClip(line_text, fontsize=60, color=NORMAL_TEXT, font=FONT, stroke_color='black', stroke_width=1, method='caption', align='center', size=(self.size[0]-200, None))\
                            .set_start(page_start).set_duration(page_end - page_start).set_position(('center', y_pos))
                        clips.append(base_txt)
                        
                        # For word-level highlighting, we'll continue using 'label' but with more safety checks
                        # If a word fails, we just skip it rather than crashing
                        line_width = base_txt.size[0]
                        current_x = (self.size[0] - line_width) // 2
                        
                        for w_info in line:
                            w_text = w_info['word'].upper()
                            try:
                                temp_w_clip = TextClip(w_text + " ", fontsize=60, font=FONT, method='label')
                                w_width = temp_w_clip.size[0]
                                temp_w_clip.close()
                                
                                highlight = TextClip(w_text, fontsize=60, color=HIGHLIGHT_TEXT, bg_color=HIGHLIGHT_BG, font=HIGHLIGHT_FONT, method='label')\
                                    .set_start(w_info['start']).set_duration(w_info['duration']).set_position((current_x, y_pos))
                                clips.append(highlight)
                                current_x += w_width
                            except:
                                continue
                    except Exception as e:
                        print(f"Caption Line Error: {e}")
                        continue
        else:
            txt = TextClip(self._wrap_text(text, 25), fontsize=70, color='white', bg_color='black', font='Nirmala-UI' if os.name == 'nt' else 'Arial', method='caption', size=(self.size[0]-100, None)).set_duration(duration).set_position('center')
            clips.append(txt)
        
        # Prioritize dedicated music folder if provided, fallback to default music/
        music_files = []
        science_music_dir = "automation/musics/science"
        if os.path.exists(science_music_dir):
            music_files += glob.glob(os.path.join(science_music_dir, "*.mp3"))
        
        if not music_files:
            # Check plural 'musics' first
            music_files = glob.glob("music/*.mp3") + glob.glob("automation/musics/*.mp3")
            if not music_files: # Fallback to singular just in case
                music_files = glob.glob("automation/music/*.mp3")

        if music_files:
            try:
                music_path = random.choice(music_files)
                print(f"Using background music: {music_path}")
                # Ensure path is absolute for moviepy
                music_path = os.path.abspath(music_path)
                bg_music = AudioFileClip(music_path).volumex(music_vol).set_duration(duration)
                
                # Gentle fades (2 seconds)
                if bg_music.duration > 4:
                    bg_music = bg_music.audio_fadein(2).audio_fadeout(2)
                
                if bg_music.duration < duration: 
                    bg_music = bg_music.fx(afx.audio_loop, duration=duration)
                
                from moviepy.audio.AudioClip import CompositeAudioClip
                # Boost voice slightly for crystal clarity
                final_audio = CompositeAudioClip([audio.volumex(1.2), bg_music])
            except Exception as e:
                print(f"Failed to load background music: {e}")
                final_audio = audio
        else:
            final_audio = audio
        
        final_video = CompositeVideoClip(clips, size=self.size).set_audio(final_audio)
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4, preset='ultrafast', logger=None)

    def _wrap_text(self, text, width):
        words, lines, curr = text.split(), [], []
        for w in words:
            if len(" ".join(curr + [w])) <= width: curr.append(w)
            else: lines.append(" ".join(curr)); curr = [w]
        lines.append(" ".join(curr))
        return "\n".join(lines)
