import time
import numpy as np
import sounddevice as sd

# pygame.midi and pygame.mixer are C extensions not yet compiled for Python 3.14.
# sounddevice is a pip-only drop-in that gives us the same pure-Python + numpy workflow.

SAMPLE_RATE = int(sd.query_devices(sd.default.device[1])['default_samplerate'])

# Additive synthesis: list of (harmonic_number, amplitude) pairs
# Violin: warm, strong upper harmonics, bowed quality
VIOLIN_HARMONICS  = [(1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.2), (6, 0.1)]
# Trumpet: bright and brassy, many loud harmonics
TRUMPET_HARMONICS = [(1, 1.0), (2, 0.9), (3, 0.8), (4, 0.7), (5, 0.5), (6, 0.3), (7, 0.2)]

def midi_to_freq(note):
    return 440.0 * 2 ** ((note - 69) / 12)

def synthesize(freq, duration, harmonics):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    wave = sum(amp * np.sin(2 * np.pi * freq * n * t) for n, amp in harmonics)

    # Simple ADSR envelope
    attack  = int(0.04 * SAMPLE_RATE)
    release = int(0.12 * SAMPLE_RATE)
    env = np.ones(len(t))
    env[:attack]   = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    wave *= env

    return wave / np.max(np.abs(wave)) * 0.45  # normalize, leave headroom for mixing

def make_audio(freq, duration):
    violin  = synthesize(freq, duration, VIOLIN_HARMONICS)
    trumpet = synthesize(freq, duration, TRUMPET_HARMONICS)
    mixed = np.clip(violin + trumpet, -1.0, 1.0)
    return mixed.astype(np.float32)

def play(audio):
    sd.play(audio, samplerate=SAMPLE_RATE)

notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale, C4–C5
chord = [60, 64, 67]                        # C major chord
NOTE_DUR  = 0.5
CHORD_DUR = 2.0

print("Playing C major scale (violin + trumpet)...")
for note in notes:
    play(make_audio(midi_to_freq(note), NOTE_DUR))
    time.sleep(0.4)
    sd.stop()
    time.sleep(0.05)

print("Playing C major chord (violin + trumpet)...")
# Mix all three chord notes into one buffer and play together
chord_audio = sum(make_audio(midi_to_freq(n), CHORD_DUR) for n in chord)
chord_audio = np.clip(chord_audio, -1.0, 1.0).astype(np.float32)
play(chord_audio)

time.sleep(CHORD_DUR)
sd.stop()
print("Done.")
