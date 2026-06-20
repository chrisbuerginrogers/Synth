import time
from collections import deque
import numpy as np
import sounddevice as sd

SAMPLE_RATE = int(sd.query_devices(sd.default.device[1])['default_samplerate'])

def midi_to_freq(note):
    return 440.0 * 2 ** ((note - 69) / 12)

# ---------------------------------------------------------------------------
# Karplus-Strong — plucked/bowed string synthesis
#
# How it works:
#   1. Fill a short circular buffer (length = one period of the note) with noise.
#   2. Each output sample is taken from the front of the buffer.
#   3. A new sample (average of two oldest * damping) is pushed onto the back.
#   4. The low-pass averaging smooths the noise into a pitched tone that decays
#      naturally — physically analogous to energy leaving a vibrating string.
# ---------------------------------------------------------------------------
def karplus_strong(freq, duration, damping=0.998):
    N = max(2, int(SAMPLE_RATE / freq))
    buf = deque(np.random.uniform(-1, 1, N))
    n_samples = int(SAMPLE_RATE * duration)
    out = np.zeros(n_samples)
    for i in range(n_samples):
        out[i] = buf[0]
        buf.append(damping * 0.5 * (buf[0] + buf[1]))
        buf.popleft()
    peak = np.max(np.abs(out))
    return out / peak if peak > 0 else out

# ---------------------------------------------------------------------------
# FM synthesis — frequency modulation for brass
#
# How it works:
#   output(t) = sin(2π·fc·t  +  I(t)·sin(2π·fm·t))
#
#   The modulator (fm) wiggles the carrier's (fc) instantaneous frequency.
#   A high modulation index I → many sidebands → bright, brassy sound.
#   Letting I decay over time mimics the trumpet's bright attack settling
#   into a warmer sustain — the key to making it sound like brass.
# ---------------------------------------------------------------------------
def fm_trumpet(freq, duration):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)

    # Modulation index: starts high (brassy attack), decays to warm sustain
    mod_index = 4.0 * np.exp(-6.0 * t / duration) + 1.5

    modulator = mod_index * np.sin(2 * np.pi * freq * t)       # fm = fc (ratio 1:1)
    carrier   = np.sin(2 * np.pi * freq * t + modulator)

    # Sharp attack, short release
    attack  = int(0.015 * SAMPLE_RATE)
    release = int(0.08  * SAMPLE_RATE)
    env = np.ones(len(t))
    env[:attack]   = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)

    wave = carrier * env
    return wave / np.max(np.abs(wave))

def make_audio(freq, duration):
    string  = karplus_strong(freq, duration)
    trumpet = fm_trumpet(freq, duration)
    n = min(len(string), len(trumpet))
    mixed = np.clip((string[:n] + trumpet[:n]) * 0.5, -1.0, 1.0)
    return mixed.astype(np.float32)

# ---------------------------------------------------------------------------

notes     = [60, 62, 64, 65, 67, 69, 71, 72]   # C major scale, C4–C5
chord     = [60, 64, 67]                         # C major chord
NOTE_DUR  = 0.6
CHORD_DUR = 3.0

print("Pre-computing audio...", flush=True)
scale_audio = [make_audio(midi_to_freq(n), NOTE_DUR) for n in notes]

n_chord = int(SAMPLE_RATE * CHORD_DUR)
chord_audio = np.zeros(n_chord, dtype=np.float32)
for note in chord:
    audio = make_audio(midi_to_freq(note), CHORD_DUR)
    chord_audio[:len(audio)] += audio
chord_audio = np.clip(chord_audio, -1.0, 1.0)

print("Playing C major scale (Karplus-Strong string + FM trumpet)...")
for audio in scale_audio:
    sd.play(audio, samplerate=SAMPLE_RATE)
    time.sleep(0.45)
    sd.stop()
    time.sleep(0.05)

time.sleep(0.2)

print("Playing C major chord (Karplus-Strong string + FM trumpet)...")
sd.play(chord_audio, samplerate=SAMPLE_RATE)
time.sleep(CHORD_DUR)
sd.stop()

print("Done.")
