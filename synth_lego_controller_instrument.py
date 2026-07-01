import time
import platform
import numpy as np
import sounddevice as sd
import fluidsynth
from lelib import controller, colorSensor

SERIAL = 1227  # both the Controller and Color Sensor are tapped with this card

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

# ── Instruments ──────────────────────────────────────────────────────────────

# Right stick direction (0–359°) divided into 5 zones of 72° each, each
# picking a different General MIDI program.
INSTRUMENTS = [
    ("Violin",       40),
    ("Trumpet",      56),
    ("Piano",         0),
    ("Flute",        73),
    ("Nylon Guitar", 24),
]

def angle_to_instrument(angle):
    zone = int((angle % 360) / 72) % 5
    return INSTRUMENTS[zone]

# ── FluidSynth ───────────────────────────────────────────────────────────────

CH = 0

sf_path = SOUNDFONTS[platform.system()]
fs   = fluidsynth.Synth(samplerate=float(SAMPLE_RATE))
sfid = fs.sfload(sf_path)
fs.program_select(CH, sfid, 0, INSTRUMENTS[0][1])
fs.cc(CH, 7, 127)  # volume pinned at max

def _render(seconds):
    raw = fs.get_samples(int(SAMPLE_RATE * seconds))
    return (np.array(raw, dtype=np.float32) / 32768).reshape(-1, 2)

# ── Main loop ─────────────────────────────────────────────────────────────────
#
# The Controller has no accelerometer, so there's no shake gesture to trigger
# a note. Instead, the separate Color Sensor is the gate: the note starts
# when something covers it and stops when it's uncovered. While the sensor
# is covered, the left stick's angle can still be moved to change the note
# and the right stick's angle switches instrument.

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
    instr_name, program = angle_to_instrument(ctl.right_angle())
    fs.program_select(CH, sfid, 0, program)
    print(f"  Blocked!  Playing {note}4 on {instr_name}...")

    fs.noteon(CH, midi, 100)

    with sd.OutputStream(samplerate=SAMPLE_RATE, channels=2, dtype='float32') as stream:
        while is_blocked(cs):
            new_note = angle_to_note(ctl.left_angle())
            new_instr_name, new_program = angle_to_instrument(ctl.right_angle())
            retrigger = new_note != note or new_program != program

            if retrigger:
                fs.noteoff(CH, midi)
                note, midi = new_note, NOTE_MIDI[new_note]
                if new_program != program:
                    fs.program_select(CH, sfid, 0, new_program)
                    instr_name, program = new_instr_name, new_program
                    print(f"  → {note}4 on {instr_name}")
                else:
                    print(f"  → {note}4")
                fs.noteon(CH, midi, 100)

            stream.write(_render(POLL_INTERVAL))

        fs.noteoff(CH, midi)
        stream.write(_render(0.08))  # flush release so noteoff doesn't clip

    print("  Unblocked. Stopped.\n")

def main():
    ctl = controller()
    cs  = colorSensor()

    print(f"Connecting to Controller (serial {SERIAL:04d})...")
    ctl.connect(card_serial=SERIAL)
    print(f"Connecting to Color Sensor (serial {SERIAL:04d})...")
    cs.connect(card_serial=SERIAL)
    print("Connected.\n")

    print("Aim the left stick to select a note; aim the right stick to pick an instrument.")
    print("Note zones:       C=0-71°  D=72-143°  E=144-215°  F=216-287°  G=288-359°")
    print("Instrument zones: Violin=0-71°  Trumpet=72-143°  Piano=144-215°  Flute=216-287°  Nylon Guitar=288-359°")
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
