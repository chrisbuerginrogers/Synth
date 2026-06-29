"""
uno_q_lego.py  —  runs ON the UNO Q (Linux, 4 GB model)

Connects directly to LEGO hardware over BLE using the legoeducation SDK,
reads motor position and shake, and plays FluidSynth audio to a paired
Bluetooth speaker over A2DP — no laptop, no PC in the chain.

Chain:
    LEGO hardware ──BLE──▶ UNO Q (this script) ──A2DP──▶ BLE speaker

Setup (run uno_q_setup.sh first, then):
    pip3 install legoeducation numpy
    python3 uno_q_lego.py

The BLE speaker must already be paired and set as the default PulseAudio sink:
    pactl set-default-sink bluez_sink.AA_BB_CC_DD_EE_FF.a2dp_sink
"""

import os
import time
import math
import sys
import fluidsynth
import numpy as np
from lelib import doubleMotor

# Route audio through lightdm's PipeWire PulseAudio socket → Bluetooth speaker
os.environ.setdefault('PULSE_SERVER', 'unix:/run/user/103/pulse/native')

# ── Config ────────────────────────────────────────────────────────────────────

SERIAL    = 27          # LEGO card serial 0027 — change to match your hardware
SOUNDFONT = "GeneralUser_GS.sf2"
CHANNEL   = 0
PROGRAM   = 40          # GM 41 = Violin; 0 = Piano, 56 = Trumpet

# ── Notes ─────────────────────────────────────────────────────────────────────

NOTE_NAMES = ['C', 'D', 'E', 'F', 'G']
NOTE_MIDI  = {'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67}

def motor_pos_to_note(abs_pos):
    zone = int(abs_pos / 72) % 5
    return NOTE_NAMES[zone]

# ── FluidSynth ────────────────────────────────────────────────────────────────
# pulseaudio driver routes audio to whatever the default PulseAudio sink is —
# set that to your BLE speaker and audio goes out over A2DP automatically.

fs   = fluidsynth.Synth()
fs.start(driver="pulseaudio")
sfid = fs.sfload(SOUNDFONT)
if sfid == -1:
    sys.exit(f"Could not load soundfont: {SOUNDFONT}")
fs.program_select(CHANNEL, sfid, 0, PROGRAM)

def play_note(midi, duration=0.5):
    fs.noteon(CHANNEL, midi, 100)
    time.sleep(duration)
    fs.noteoff(CHANNEL, midi)
    time.sleep(0.08)   # let release tail fade

# ── Shake detection ───────────────────────────────────────────────────────────

SHAKE_VARIANCE_THRESHOLD = 400_000
SHAKE_WINDOW_SECS        = 1.0
POLL_HZ                  = 20
POLL_INTERVAL            = 1.0 / POLL_HZ

def accel_magnitude(dm):
    imu = dm.imu_device
    return math.sqrt(imu.accelerometerX**2 + imu.accelerometerY**2 + imu.accelerometerZ**2)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    dm = doubleMotor()
    print(f"Connecting to LEGO Double Motor (serial {SERIAL:04d}) over BLE...")
    dm.connect(card_serial=SERIAL)
    print("Connected.\n")
    print(f"FluidSynth ready — program {PROGRAM} → BLE speaker via PulseAudio A2DP")
    print("Turn the left motor to select a note, shake to play.")
    print("Zones: C=0-71°  D=72-143°  E=144-215°  F=216-287°  G=288-359°\n")

    mag_window = []
    last_note  = None
    playing    = False

    while True:
        now     = time.time()
        abs_pos = dm.motor[0].absolutePosition
        note    = motor_pos_to_note(abs_pos)
        midi    = NOTE_MIDI[note]

        if note != last_note:
            print(f"  Motor {abs_pos:3d}°  →  {note}4  (MIDI {midi})")
            last_note = note

        mag = accel_magnitude(dm)
        mag_window.append((now, mag))
        mag_window = [(t, m) for t, m in mag_window if now - t <= SHAKE_WINDOW_SECS]

        min_samples = int(SHAKE_WINDOW_SECS * POLL_HZ * 0.8)
        if not playing and len(mag_window) >= min_samples:
            variance = float(np.var([m for _, m in mag_window]))
            if variance > SHAKE_VARIANCE_THRESHOLD:
                print(f"  Shake!  Playing {note}4...")
                playing = True
                play_note(midi)
                playing = False
                mag_window.clear()
                print()

        elapsed = time.time() - now
        time.sleep(max(0, POLL_INTERVAL - elapsed))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fs.delete()
