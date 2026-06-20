import fluidsynth
import numpy as np
import sounddevice as sd
import platform
import sys

# Match FluidSynth's render rate to whatever the OS output device natively runs at.
# Mismatches (e.g. 44100 vs AirPods' 48000) cause sd.play() to fail silently.
SAMPLE_RATE = int(sd.query_devices(sd.default.device[1])['default_samplerate'])

SOUNDFONTS = {
    "Darwin":  "GeneralUser_GS.sf2",
    "Windows": "GeneralUser_GS.sf2",
    "Linux":   "GeneralUser_GS.sf2",
}

OS = platform.system()
if OS not in SOUNDFONTS:
    print(f"Unsupported OS: {OS}")
    sys.exit(1)

VIOLIN_CH  = 0  # General MIDI program 40
TRUMPET_CH = 1  # General MIDI program 56

fs = fluidsynth.Synth(samplerate=float(SAMPLE_RATE))
sfid = fs.sfload(SOUNDFONTS[OS])
fs.program_select(VIOLIN_CH,  sfid, 0, 40)
fs.program_select(TRUMPET_CH, sfid, 0, 56)

def render(seconds):
    n_samples = int(SAMPLE_RATE * seconds)
    raw = fs.get_samples(n_samples)
    return (np.array(raw, dtype=np.float32) / 32768).reshape(-1, 2)

def render_scale(channels):
    chunks = []
    for note in notes:
        for ch in channels:
            fs.noteon(ch, note, 100)
        chunks.append(render(NOTE_DUR))
        for ch in channels:
            fs.noteoff(ch, note)
        chunks.append(render(GAP_DUR))
    return np.concatenate(chunks)

def render_chord(channels):
    for note in chord:
        for ch in channels:
            fs.noteon(ch, note, 100)
    audio = render(CHORD_DUR)
    for note in chord:
        for ch in channels:
            fs.noteoff(ch, note)
    render(0.1)  # flush release tail
    return audio

notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale, C4–C5
chord = [60, 64, 67]                        # C major chord
NOTE_DUR  = 0.45
GAP_DUR   = 0.05
CHORD_DUR = 1.5

print("Pre-rendering audio...")

violin_scale  = render_scale([VIOLIN_CH])
violin_chord  = render_chord([VIOLIN_CH])

trumpet_scale = render_scale([TRUMPET_CH])
trumpet_chord = render_chord([TRUMPET_CH])

both_scale    = render_scale([VIOLIN_CH, TRUMPET_CH])
both_chord    = render_chord([VIOLIN_CH, TRUMPET_CH])

fs.delete()

def play(scale, chord_audio):
    print(f"  Scale...")
    sd.play(scale, samplerate=SAMPLE_RATE)
    sd.wait()
    print(f"  Chord...")
    sd.play(chord_audio, samplerate=SAMPLE_RATE)
    sd.wait()

print("\nViolin:")
play(violin_scale, violin_chord)

print("\nTrumpet:")
play(trumpet_scale, trumpet_chord)

print("\nViolin + Trumpet together:")
play(both_scale, both_chord)

print("\nDone.")
