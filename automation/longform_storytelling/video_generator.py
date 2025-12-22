import os
import numpy as np
import random
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    TextClip, ColorClip, CompositeVideoClip, AudioFileClip, 
    ImageClip, VideoFileClip, concatenate_videoclips
)
from moviepy.video.fx.all import resize

class StoryVideoGenerator:
    def __init__(self, size=(1920, 1080)):
        self.size = size
        self.asset_dir = "automation/longform_storytelling/assets"
        self.font_path = "automation/media/assets/NotoSansDevanagari-Regular.ttf"
        
        self.emotion_map = {
            "Smiling": "smiling",
            "Amused": "smiling",
            "Surprised": "surprised",
            "Neutral": "neutral",
            "Thoughtful": "neutral",
            "Annoyed": "neutral"
        }

    def _get_character_clip(self, char: str, emotion: str, duration: float, position: str):
        suffix = self.emotion_map.get(emotion, "neutral")
        filename = f"{char.lower()}_{suffix}.png"
        path = os.path.join(self.asset_dir, filename)
        
        if not os.path.exists(path):
            path = os.path.join(self.asset_dir, f"{char.lower()}_neutral.png")
            if not os.path.exists(path):
                return ColorClip(size=(400, 600), color=(100, 100, 100)).set_duration(duration)

        with Image.open(path) as img:
            # User refinement: Baje (left) looks RIGHT, Arav (right) looks LEFT
            # We assume original images might be inconsistent, so we flip based on role
            if char.lower() == "baje":
                # If Baje needs to look right, we might need to flip if he currently looks left
                # For now, let's just make sure he's flipped to face the center (right)
                img = img.transpose(Image.FLIP_LEFT_RIGHT)
            # Arav on right looks LEFT, so if he faces right, flip him
            # We'll apply flip logic to ensure they face each other
            
            # Simple heuristic: Baje always flipped, Arav kept as is (assuming default faces right)
            # Or better, just apply flip to Baje to face Right, and keep Arav to face Left.
            
            # Since I can't see the images, I'll provide a 'facing' adjustment
            clip_img = np.array(img.convert('RGBA'))

        clip = ImageClip(clip_img).set_duration(duration)
        clip = clip.resize(height=900)
        
        # Position
        if position == "left":
            clip = clip.set_position((150, 180)) 
        else:
            clip = clip.set_position((self.size[0] - clip.size[0] - 150, 180)) 
            
        return clip

    def _get_karaoke_subtitles(self, text: str, duration: float, word_offsets: List[Dict], start_time: float):
        """
        Creates a centered karaoke subtitle clip with yellow highlighting.
        """
        fsize = 70
        max_width = 1200
        
        try:
            font = ImageFont.truetype(self.font_path, fsize)
        except:
            font = ImageFont.load_default()

        # Wrap text and track coordinates
        words = text.split()
        lines = []
        curr_line = []
        curr_width = 0
        
        for w in words:
            w_width = font.getbbox(w + " ")[2] - font.getbbox(w + " ")[0]
            if curr_width + w_width < max_width:
                curr_line.append(w)
                curr_width += w_width
            else:
                lines.append(curr_line)
                curr_line = [w]
                curr_width = w_width
        lines.append(curr_line)

        # Base image with full white text
        dummy = Image.new('RGBA', (self.size[0], 300))
        d = ImageDraw.Draw(dummy)
        
        # Calculate vertical start
        line_height = fsize + 20
        total_h = len(lines) * line_height
        y_offset = (300 - total_h) // 2
        
        word_positions = {} # word_index -> (x, y, text)
        w_idx = 0
        
        for l_idx, line in enumerate(lines):
            line_str = " ".join(line)
            lw = d.textbbox((0, 0), line_str, font=font)[2]
            x_cursor = (self.size[0] - lw) // 2
            
            for word in line:
                word_positions[w_idx] = (x_cursor, y_offset + l_idx * line_height, word)
                x_cursor += d.textbbox((0, 0), word + " ", font=font)[2]
                w_idx += 1

        # Create clips
        karaoke_clips = []
        
        # 1. Base (White) Clip for the whole duration
        base_img = Image.new('RGBA', (self.size[0], 300), (0, 0, 0, 0))
        bd = ImageDraw.Draw(base_img)
        for idx, (x, y, word) in word_positions.items():
            bd.text((x, y), word, font=font, fill="white", stroke_width=2, stroke_fill="black")
        
        base_clip = ImageClip(np.array(base_img)).set_duration(duration).set_position(('center', 750))
        karaoke_clips.append(base_clip)
        
        # 2. Highlight (Yellow) Clips for each word using offsets
        # We need to match word_offsets to our words
        for i, offset in enumerate(word_offsets):
            if i in word_positions:
                x, y, word = word_positions[i]
                
                # Create a small image for just this yellow word
                w_bbox = d.textbbox((0, 0), word, font=font)
                ww, wh = w_bbox[2] - w_bbox[0], w_bbox[3] - w_bbox[1]
                
                word_img = Image.new('RGBA', (ww + 10, wh + 10), (0, 0, 0, 0))
                wd = ImageDraw.Draw(word_img)
                wd.text((5, 5), word, font=font, fill="yellow", stroke_width=2, stroke_fill="black")
                
                w_dur = max(0.1, offset['duration'])
                w_start = offset['start'] - start_time
                
                if w_start < 0: w_start = 0
                if w_start + w_dur > duration: w_dur = duration - w_start
                
                if w_dur > 0:
                    w_clip = ImageClip(np.array(word_img)).set_duration(w_dur).set_start(w_start)
                    w_clip = w_clip.set_position((x - 5, 750 + y - 5))
                    karaoke_clips.append(w_clip)
        
        return karaoke_clips

    def create_story_video(self, script: List[Dict], audio_path: str, output_path: str):
        audio = AudioFileClip(audio_path)
        total_duration = audio.duration
        
        # Background: Gradient or nice color
        bg = ColorClip(size=self.size, color=(20, 30, 50)).set_duration(total_duration)
        
        # Add subtle Ken Burns to background if we had an image, 
        # but since we have a solid color, we'll just use it.
        # Let's add the characters and subtitles for each segment
        
        clips = [bg]
        
        for line in script:
            start = line.get('audio_start', 0)
            dur = line.get('audio_duration', 0)
            speaker = line['speaker']
            emotion = line['emotion']
            text = line['text']
            word_offsets = line.get('word_offsets', [])
            
            # Show active speaker with emotion
            if speaker == "बाजे":
                char_clip = self._get_character_clip("baje", emotion, dur, "left")
                clips.append(char_clip.set_start(start))
            else:
                char_clip = self._get_character_clip("arav", emotion, dur, "right")
                clips.append(char_clip.set_start(start))
                
            # Add Centered Karaoke Subtitles
            # Each segment of audio has its own word offsets
            line_sub_clips = self._get_karaoke_subtitles(text, dur, word_offsets, start)
            for s_clip in line_sub_clips:
                clips.append(s_clip.set_start(start))
            
            # Simple "zoom" effect on active speaker
            # char_clip = char_clip.resize(lambda t: 1.0 + 0.05 * (t/dur)) 
            # (MoviePy's resize with lambda can be slow, let's do it carefully if needed)

        final_video = CompositeVideoClip(clips, size=self.size).set_audio(audio)
        
        # Add background music
        music_dir = "music"
        if os.path.exists(music_dir):
            music_files = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3")]
        else:
            music_files = []
        if music_files:
            try:
                music_path = random.choice(music_files)
                bg_music = AudioFileClip(music_path).volumex(0.1).set_duration(total_duration)
                from moviepy.audio.AudioClip import CompositeAudioClip
                final_audio = CompositeAudioClip([audio.volumex(1.2), bg_music])
                final_video = final_video.set_audio(final_audio)
            except:
                pass

        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", threads=4)
        return output_path

if __name__ == "__main__":
    # Minimal test
    gen = StoryVideoGenerator()
    # Mock data
    mock_script = [
        {"speaker": "बाजे", "emotion": "Smiling", "text": "नमस्ते आरव!", "audio_start": 0, "audio_duration": 2},
        {"speaker": "आरव", "emotion": "Neutral", "text": "नमस्ते बाजे, के छ खबर?", "audio_start": 2, "audio_duration": 3}
    ]
    # This requires an actual audio file to run correctly in a real test
    print("Video Generator code implemented. Run end-to-end to test.")
