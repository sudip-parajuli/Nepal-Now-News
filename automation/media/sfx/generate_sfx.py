"""
Generate minimal SFX files (whoosh.mp3 and dong.mp3) for scene transitions.
Uses numpy+scipy for WAV generation, then ffmpeg to convert to MP3.
Run this once to populate automation/media/sfx/.
"""
import os
import sys
import struct
import wave
import math

SFX_DIR = os.path.dirname(os.path.abspath(__file__))


def write_wav(filename: str, samples, sample_rate: int = 44100):
    """Write a list of float samples [-1, 1] to a 16-bit mono WAV file."""
    path = os.path.join(SFX_DIR, filename)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        packed = struct.pack(f'<{len(samples)}h',
                             *[max(-32767, min(32767, int(s * 32767))) for s in samples])
        wf.writeframes(packed)
    print(f"[SFX] Generated WAV: {path}")
    return path


def convert_to_mp3(wav_path: str):
    """Convert WAV to MP3 using ffmpeg if available, otherwise keep WAV."""
    mp3_path = wav_path.replace('.wav', '.mp3')
    try:
        import subprocess
        result = subprocess.run(
            ['ffmpeg', '-y', '-i', wav_path, '-acodec', 'libmp3lame',
             '-ab', '128k', mp3_path],
            capture_output=True, timeout=30
        )
        if result.returncode == 0:
            os.remove(wav_path)
            print(f"[SFX] Converted to MP3: {mp3_path}")
            return mp3_path
    except Exception as e:
        print(f"[SFX] ffmpeg MP3 conversion failed: {e}. Keeping WAV as .mp3 name.")
    # Rename WAV to .mp3 as a fallback (MoviePy can read WAV regardless)
    os.rename(wav_path, mp3_path)
    return mp3_path


def generate_whoosh(duration=0.4, sample_rate=44100):
    """
    A rising-pitch filtered noise burst → cinematic 'whoosh' effect.
    Simulates a swept band-pass noise from 200 Hz → 2000 Hz.
    """
    n = int(duration * sample_rate)
    samples = []
    for i in range(n):
        t = i / sample_rate
        # Amplitude envelope: quick attack, smooth decay
        env = math.exp(-t * 6) * (1 - math.exp(-t * 40))
        # White noise approximation via multiple sine waves (pseudo-noise)
        noise = 0.0
        for freq in [200, 400, 700, 1100, 1600, 2200, 3200, 4800]:
            phase_noise = math.sin(freq * 2 * math.pi * t + freq * 0.001 * i)
            noise += phase_noise / 8
        # Frequency sweep gives the 'whoosh' feel
        sweep_freq = 200 + (2000 - 200) * (t / duration) ** 0.5
        sweep = math.sin(2 * math.pi * sweep_freq * t) * 0.3
        sample = (noise + sweep) * env * 0.7
        samples.append(sample)
    return samples


def generate_dong(duration=1.2, sample_rate=44100):
    """
    A soft metallic 'dong' / bell strike with exponential decay.
    Combines fundamental + harmonics for a bell-like timbre.
    """
    n = int(duration * sample_rate)
    fundamental = 440.0   # A4
    harmonics = [
        (1.0, 1.00),    # fundamental
        (2.76, 0.50),   # inharmonic partial 1
        (5.40, 0.25),   # inharmonic partial 2
        (8.93, 0.12),   # inharmonic partial 3
        (13.34, 0.06),  # inharmonic partial 4
    ]
    samples = []
    for i in range(n):
        t = i / sample_rate
        env = math.exp(-t * 3.5)      # Bell decay
        attack_env = 1 - math.exp(-t * 200)  # Quick attack
        sample = 0.0
        for ratio, amp in harmonics:
            freq = fundamental * ratio
            sample += amp * math.sin(2 * math.pi * freq * t)
        sample *= env * attack_env * 0.6
        samples.append(sample)
    return samples


def generate_transition_sweep(duration=0.25, sample_rate=44100):
    """
    A quick upward frequency sweep for cut transitions.
    """
    n = int(duration * sample_rate)
    samples = []
    for i in range(n):
        t = i / sample_rate
        env = (1 - t / duration) ** 2  # Linear decay
        freq = 300 + 3000 * (t / duration) ** 2
        sample = math.sin(2 * math.pi * freq * t) * env * 0.5
        samples.append(sample)
    return samples


if __name__ == '__main__':
    print("[SFX] Generating science transition sound effects...")

    # Generate whoosh
    whoosh_wav = write_wav('whoosh.wav', generate_whoosh())
    convert_to_mp3(whoosh_wav)

    # Generate dong
    dong_wav = write_wav('dong.wav', generate_dong())
    convert_to_mp3(dong_wav)

    # Generate sweep
    sweep_wav = write_wav('sweep.wav', generate_transition_sweep())
    convert_to_mp3(sweep_wav)

    print("[SFX] All SFX generated successfully!")
