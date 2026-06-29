import time
import math
import platform
import numpy as np
import sounddevice as sd
import fluidsynth
from lelib import doubleMotor

SERIAL = 27  # card serial 0027

SAMPLE_RATE = int(sd.query_devices(sd.default.device[1])['default_samplerate'])

SOUNDFONTS = {
    "Darwin":  "GeneralUser_GS.sf2",
    "Windows": "GeneralUser_GS.sf2",
    "Linux":   "GeneralUser_GS.sf2",
}

# ── Notes ────────────────────────────────────────────────────────────────────

# Left motor absolute position (0–359°) divided into 5 zones of 72° each
NOTE_NAMES = ['C', 'D', 'E', 'F', 'G']
NOTE_MIDI  = {'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67}  # octave 4

def motor_pos_to_note(abs_pos):
    zone = int(abs_pos / 72) % 5
    return NOTE_NAMES[zone]

# ── FluidSynth ───────────────────────────────────────────────────────────────

VIOLIN_CH  = 0   # General MIDI program 40
TRUMPET_CH = 1   # General MIDI program 56

sf_path = SOUNDFONTS[platform.system()]
fs   = fluidsynth.Synth(samplerate=float(SAMPLE_RATE))
sfid = fs.sfload(sf_path)
fs.program_select(VIOLIN_CH,  sfid, 0, 40)
fs.program_select(TRUMPET_CH, sfid, 0, 56)

def play_note(note_name, duration=0.5):
    midi = NOTE_MIDI[note_name]
    for ch in [VIOLIN_CH, TRUMPET_CH]:
        fs.noteon(ch, midi, 100)
    audio = _render(duration)
    for ch in [VIOLIN_CH, TRUMPET_CH]:
        fs.noteoff(ch, midi)
    tail = _render(0.08)   # flush release so noteoff doesn't clip
    sd.play(np.concatenate([audio, tail]), samplerate=SAMPLE_RATE)
    sd.wait()

def _render(seconds):
    raw = fs.get_samples(int(SAMPLE_RATE * seconds))
    return (np.array(raw, dtype=np.float32) / 32768).reshape(-1, 2)

# ── Shake detection ───────────────────────────────────────────────────────────
#
# Accelerometer units are milliG (1 g ≈ 1000). At rest, magnitude ≈ 1000.
# Shaking produces rapid oscillation — detected as high variance over 1 second.
# Raise SHAKE_VARIANCE_THRESHOLD if spurious triggers occur; lower if missed.

SHAKE_VARIANCE_THRESHOLD = 400_000   # (mg)²
SHAKE_WINDOW_SECS        = 1.0
POLL_HZ                  = 20
POLL_INTERVAL            = 1.0 / POLL_HZ

def _accel_magnitude(dm):
    imu = dm.imu_device
    return math.sqrt(imu.accelerometerX**2 + imu.accelerometerY**2 + imu.accelerometerZ**2)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    dm = doubleMotor()
    print(f"Connecting to Double Motor (serial {SERIAL:04d})...")
    dm.connect(card_serial=SERIAL)
    print("Connected.\n")
    print("Turn the left motor to select a note, then shake for 1 second to play it.")
    print("Zones: C=0-71°  D=72-143°  E=144-215°  F=216-287°  G=288-359°\n")

    mag_window = []
    last_note  = None
    playing    = False

    while True:
        now     = time.time()
        abs_pos = dm.motor[0].absolutePosition
        note    = motor_pos_to_note(abs_pos)

        if note != last_note:
            print(f"  Motor {abs_pos:3d}°  →  {note}4")
            last_note = note

        mag = _accel_magnitude(dm)
        mag_window.append((now, mag))
        mag_window = [(t, m) for t, m in mag_window if now - t <= SHAKE_WINDOW_SECS]

        min_samples = int(SHAKE_WINDOW_SECS * POLL_HZ * 0.8)
        if not playing and len(mag_window) >= min_samples:
            variance = float(np.var([m for _, m in mag_window]))
            if variance > SHAKE_VARIANCE_THRESHOLD:
                print(f"  Shake!  Playing {note}4...")
                playing = True
                play_note(note)
                playing = False
                mag_window.clear()
                print()

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
