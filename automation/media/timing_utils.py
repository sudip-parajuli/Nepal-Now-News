import re

def calculate_adjusted_durations(scenes, fps=30) -> list[float]:
    """
    Calculates adjusted visual scene durations accounting for transitions.
    Formula:
    - Each flash adds 2/fps = 0.0667s to total duration
    - Each fade removes fade_overlap_seconds (0.5s)
    """
    durations = []
    transitions = []
    for i in range(len(scenes) - 1):
        next_type = scenes[i+1].get("visual_type")
        curr_type = scenes[i].get("visual_type")
        if next_type in ("hook_question", "kinetic_stat"):
            transitions.append("flash")
        elif (curr_type == "image" and next_type == "ai_video") or (curr_type == "ai_video" and next_type == "image"):
            transitions.append("fade")
        else:
            transitions.append("cut")
            
    for i, scene in enumerate(scenes):
        base_dur = 5.0 # default base visual duration if none specified
        before_t = transitions[i-1] if i > 0 else None
        after_t = transitions[i] if i < len(transitions) else None
        
        adj_dur = base_dur
        if before_t == "fade":
            adj_dur += 0.5
        if after_t == "flash":
            adj_dur += 0.0667
        durations.append(adj_dur)
    return durations

def match_scenes_to_timestamps(scenes, word_offsets, total_duration):
    """
    Sequentially matches each scene's narration words to the continuous list of word_offsets.
    Returns a list of dicts: {"start": float, "end": float, "duration": float, "word_times": list[float]}.
    """
    def clean_word(w):
        return re.sub(r'[^a-zA-Z0-9]', '', w).lower()
        
    cleaned_offsets = [clean_word(w["word"]) for w in word_offsets]
    current_offset_idx = 0
    num_offsets = len(word_offsets)
    scene_timings = []
    
    for idx, scene in enumerate(scenes):
        narration = scene.get("narration", "")
        scene_words = [clean_word(w) for w in narration.split() if clean_word(w)]
        if not scene_words or not word_offsets:
            scene_timings.append({
                "start": idx * (total_duration / max(1, len(scenes))),
                "end": (idx + 1) * (total_duration / max(1, len(scenes))),
                "word_times": [0.0]
            })
            continue
            
        start_time = None
        matched_offsets_indices = []
        for sw in scene_words:
            found = False
            for j in range(current_offset_idx, min(current_offset_idx + 100, num_offsets)):
                if cleaned_offsets[j] == sw:
                    matched_offsets_indices.append(j)
                    current_offset_idx = j + 1
                    found = True
                    break
            if not found:
                if current_offset_idx < num_offsets:
                    matched_offsets_indices.append(current_offset_idx)
                    current_offset_idx += 1
                    
        if matched_offsets_indices:
            start_time = word_offsets[matched_offsets_indices[0]]["start"]
            last_w = word_offsets[matched_offsets_indices[-1]]
            end_time = last_w["start"] + last_w["duration"]
            word_times = [word_offsets[idx]["start"] - start_time for idx in matched_offsets_indices]
        else:
            start_time = current_offset_idx / max(1, num_offsets) * total_duration
            end_time = (current_offset_idx + len(scene_words)) / max(1, num_offsets) * total_duration
            word_times = [0.0] * len(scene_words)
            
        scene_timings.append({
            "start": start_time,
            "end": end_time,
            "word_times": word_times
        })
        
    # Calibrate starts/ends sequentially to guarantee absolute coverage
    if scene_timings:
        scene_timings[0]["start"] = 0.0
        for i in range(1, len(scene_timings)):
            prev_end = scene_timings[i-1]["end"]
            scene_timings[i]["start"] = prev_end
            if scene_timings[i]["end"] <= prev_end:
                scene_timings[i]["end"] = prev_end + 3.0
        scene_timings[-1]["end"] = total_duration
        
    for item in scene_timings:
        item["duration"] = max(0.1, item["end"] - item["start"])
        
    return scene_timings
