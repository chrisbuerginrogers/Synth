"""
FluidSynth driven by the IK Multimedia UNO Q keyboard over CoreMIDI.

Usage:
    python3 uno_q.py [soundfont.sf2]

Controls:
    Play keys on the UNO Q — FluidSynth renders audio through the Mac speakers.
    Ctrl-C to quit.
"""

import sys
import time
import platform
import signal
import fluidsynth

SOUNDFONT = sys.argv[1] if len(sys.argv) > 1 else "GeneralUser_GS.sf2"
CHANNEL   = 0
PROGRAM   = 0   # Acoustic Grand Piano (GM program 1)

def main():
    fs = fluidsynth.Synth()

    # CoreAudio for output, CoreMIDI for input
    fs.start(driver="coreaudio", midi_driver="coremidi")

    sfid = fs.sfload(SOUNDFONT)
    if sfid == -1:
        sys.exit(f"Could not load soundfont: {SOUNDFONT}")

    fs.program_select(CHANNEL, sfid, 0, PROGRAM)
    print(f"FluidSynth ready — soundfont: {SOUNDFONT}, program: {PROGRAM}")
    print("Play keys on the UNO Q. Ctrl-C to quit.")

    # Block until interrupted; FluidSynth handles MIDI events in its own thread
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
