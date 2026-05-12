import datetime

def format_timestamp(seconds: float) -> str:
    """Converts seconds into SRT timestamp format HH:MM:SS,mmm"""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generate_srt(word_offsets: list, output_path: str, words_per_caption: int = 8):
    """
    Converts word offsets to a standard SRT subtitle file.
    Groups words into chunks for readability.
    """
    if not word_offsets:
        return None
        
    srt_content = []
    chunk = []
    
    # We group words into chunks of 'words_per_caption' for better flow in long form
    # but we also respect pauses (large gaps between words)
    
    for i, offset in enumerate(word_offsets):
        chunk.append(offset)
        
        # Check if we should flush the chunk
        flush = False
        if len(chunk) >= words_per_caption:
            flush = True
        elif i < len(word_offsets) - 1:
            # If the next word starts more than 1.5s after this one ends, flush
            gap = word_offsets[i+1]['start'] - (offset['start'] + offset['duration'])
            if gap > 1.5:
                flush = True
        else:
            # Last word
            flush = True
            
        if flush:
            start_time = chunk[0]['start']
            # End time is end of last word in chunk, but maybe extended slightly
            end_time = chunk[-1]['start'] + chunk[-1]['duration']
            
            # Ensure it's not too short (min 1 second if possible)
            if end_time - start_time < 1.0 and i < len(word_offsets) - 1:
                 # Don't overlap with next word though
                 end_time = min(start_time + 1.0, word_offsets[i+1]['start'])
            
            text = " ".join([w['word'] for w in chunk])
            # Strip emotional tags and formatting asterisks
            import re
            text = re.sub(r'\[.*?\]', '', text).replace('*', '').strip()
            
            idx = len(srt_content) + 1
            srt_content.append(f"{idx}")
            srt_content.append(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}")
            srt_content.append(f"{text}\n")
            chunk = []
            
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_content))
        
    return output_path
