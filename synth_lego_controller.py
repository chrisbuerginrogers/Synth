import time
import platform
import numpy as np
import sounddevice as sd
import fluidsynth
from lelib import controller, colorSensor

CONTROLLER_SERIAL   = 1227  # card serial 0027
COLOR_SENSOR_SERIAL = 3664  # change to match your color sensor's card

SAMPLE_RATE = int(sd.query_devices(sd.default.device[1])['default_samplerate'])

SOUNDFONTS = {
    "Darwin":  "GeneralUser_GS.sf2",
    "Windows": "GeneralUser_GS.sf2",
    "Linux":   "GeneralUser_GS.sf2",
}

# ── Notes ────────────────────────────────────────────────────────────────────

# Left stick direction (0–359°) divided into 5 zones of 72° each
NOTE_NAMES = ['C', 'D', 'E', 'F', 'G']
NOTE_MIDI  = {'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67}  # octave 4

def angle_to_note(angle):
    zone = int((angle % 360) / 72) % 5
    return NOTE_NAMES[zone]

# Right stick direction (0–359°) mapped linearly onto a MIDI channel-volume
# range. Floor kept above 0 so no angle plays an inaudibly quiet note.
MIN_VOLUME = 20
MAX_VOLUME = 127

def angle_to_volume(angle):
    pct = (angle % 360) / 360
    return int(MIN_VOLUME + pct * (MAX_VOLUME - MIN_VOLUME))

# ── FluidSynth ───────────────────────────────────────────────────────────────

VIOLIN_CH  = 0   # General MIDI program 40
TRUMPET_CH = 1   # General MIDI program 56
CHANNELS   = [VIOLIN_CH, TRUMPET_CH]

sf_path = SOUNDFONTS[platform.system()]
fs   = fluidsynth.Synth(samplerate=float(SAMPLE_RATE))
sfid = fs.sfload(sf_path)
fs.program_select(VIOLIN_CH,  sfid, 0, 40)
fs.program_select(TRUMPET_CH, sfid, 0, 56)

def _render(seconds):
    raw = fs.get_samples(int(SAMPLE_RATE * seconds))
    return (np.array(raw, dtype=np.float32) / 32768).reshape(-1, 2)

# ── Main loop ─────────────────────────────────────────────────────────────────
#
# The Controller has no accelerometer, so there's no shake gesture to trigger
# a note. Instead, the separate Color Sensor is the gate: the note starts
# when something covers it and stops when it's uncovered. While the sensor
# is covered, the left stick's angle can still be moved to change the note
# and the right stick's angle continuously sets volume.

POLL_HZ       = 20
POLL_INTERVAL = 1.0 / POLL_HZ

def is_blocked(cs):
    """True while something covers the color sensor.
    Assumes an uncovered sensor reports 'No color'; if that's noisy on your
    hardware, swap in a reflection() threshold instead."""
    return cs.detect_color() != 'No color'

def sustain_while_blocked(ctl, cs):
    note = angle_to_note(ctl.left_angle())
    midi = NOTE_MIDI[note]
    print(f"  Blocked!  Playing {note}4...")

    for ch in CHANNELS:
        fs.cc(ch, 7, angle_to_volume(ctl.right_angle()))
        fs.noteon(ch, midi, 100)

    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=2, dtype='float32') as stream:
        while is_blocked(cs):
            new_note = angle_to_note(ctl.left_angle())
            if new_note != note:
                for ch in CHANNELS:
                    fs.noteoff(ch, midi)
                note, midi = new_note, NOTE_MIDI[new_note]
                for ch in CHANNELS:
                    fs.noteon(ch, midi, 100)
                print(f"  → {note}4")

            for ch in CHANNELS:
                fs.cc(ch, 7, angle_to_volume(ctl.right_angle()))

            stream.write(_render(POLL_INTERVAL))

        for ch in CHANNELS:
            fs.noteoff(ch, midi)
        stream.write(_render(0.08))  # flush release so noteoff doesn't clip

    print("  Unblocked. Stopped.\n")

def main():
    ctl = controller()
    cs  = colorSensor()

    print(f"Connecting to Controller (serial {CONTROLLER_SERIAL:04d})...")
    ctl.connect(card_serial=CONTROLLER_SERIAL)
    print(f"Connecting to Color Sensor (serial {COLOR_SENSOR_SERIAL:04d})...")
    cs.connect(card_serial=COLOR_SENSOR_SERIAL)
    print("Connected.\n")

    print("Aim the left stick to select a note; aim the right stick to set volume.")
    print("Zones: C=0-71°  D=72-143°  E=144-215°  F=216-287°  G=288-359°")
    print("Cover the color sensor to play; uncover it to stop.\n")

    last_note = None

    while True:
        note = angle_to_note(ctl.left_angle())
        if note != last_note:
            print(f"  Left stick {ctl.left_angle():3d}°  →  {note}4")
            last_note = note

        if is_blocked(cs):
            sustain_while_blocked(ctl, cs)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
