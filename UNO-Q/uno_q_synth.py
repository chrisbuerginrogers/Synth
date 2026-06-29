"""
uno_q_synth.py  —  runs ON the UNO Q (Linux, 4 GB model)

Receives BLE MIDI from the LEGO hub, renders audio with FluidSynth,
and streams it to a paired BLE speaker via ALSA → PipeWire/PulseAudio → BlueZ A2DP.

Setup on the UNO Q (run once):
    pip3 install bleak
    apt-get install -y fluidsynth python3-pyfluidsynth

Pair the BLE speaker once from the UNO Q shell:
    bluetoothctl
    > power on
    > agent on
    > scan on
    # wait for speaker to appear, note its MAC address
    > pair   AA:BB:CC:DD:EE:FF
    > trust  AA:BB:CC:DD:EE:FF
    > connect AA:BB:CC:DD:EE:FF
    > quit

Then run:
    python3 uno_q_synth.py [soundfont.sf2]
"""

import asyncio
import sys
import time
import fluidsynth
from bleak import BleakScanner, BleakClient

# ── Config ────────────────────────────────────────────────────────────────────

SOUNDFONT = sys.argv[1] if len(sys.argv) > 1 else "GeneralUser_GS.sf2"
CHANNEL   = 0
PROGRAM   = 40   # GM 41 = Violin; change to 0 for piano, 56 for trumpet, etc.

# BLE MIDI UUIDs (standard)
BLE_MIDI_SERVICE        = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"
BLE_MIDI_CHARACTERISTIC = "7772e5db-3868-4112-a1a9-f2669d106bf3"

# ── FluidSynth setup ──────────────────────────────────────────────────────────

def start_fluidsynth():
    # "pulseaudio" works when PulseAudio/PipeWire is running and the BLE
    # speaker is the default sink (set with: pactl set-default-sink <sink>)
    fs = fluidsynth.Synth()
    fs.start(driver="pulseaudio")
    sfid = fs.sfload(SOUNDFONT)
    if sfid == -1:
        sys.exit(f"Could not load soundfont: {SOUNDFONT}")
    fs.program_select(CHANNEL, sfid, 0, PROGRAM)
    print(f"FluidSynth ready — program {PROGRAM} on channel {CHANNEL}")
    return fs

# ── BLE MIDI packet parser ────────────────────────────────────────────────────
# Packet layout: [header, timestamp, status, note, velocity, ...]
# May contain multiple events; each status byte resets parsing.

def parse_ble_midi(data: bytes):
    """Yield (status, note, velocity) tuples from a BLE MIDI packet."""
    if len(data) < 3:
        return
    i = 1   # skip header byte
    while i < len(data) - 1:
        # timestamp byte (bit 7 set, bit 6 set)
        if data[i] & 0x80:
            i += 1   # consume timestamp
        if i >= len(data):
            break
        status = data[i]
        if status & 0x80:   # it's a status byte
            msg_type = status & 0xF0
            if msg_type in (0x80, 0x90) and i + 2 < len(data):
                note     = data[i + 1] & 0x7F
                velocity = data[i + 2] & 0x7F
                yield (status, note, velocity)
                i += 3
            else:
                i += 1
        else:
            i += 1

# ── BLE MIDI scan ─────────────────────────────────────────────────────────────

HUB_NAME = "LegoSynth"   # must match HUB_NAME in lego_instrument.py

async def find_lego_sender():
    print(f"Scanning for '{HUB_NAME}' BLE MIDI sender (10 s)...")
    devices = await BleakScanner.discover(timeout=10.0, service_uuids=[BLE_MIDI_SERVICE])
    if not devices:
        raise RuntimeError(
            "No BLE MIDI device found.\n"
            "Make sure the LEGO hub is running lego_instrument.py and is nearby."
        )
    for d in devices:
        if d.name and HUB_NAME in d.name:
            print(f"Found hub: {d.name} ({d.address})")
            return d.address
    # fall back to first device found
    d = devices[0]
    print(f"Found BLE MIDI sender: {d.name} ({d.address})")
    return d.address

# ── Main ──────────────────────────────────────────────────────────────────────

async def run():
    fs = start_fluidsynth()

    address = await find_lego_sender()

    def on_midi(sender, data: bytearray):
        for status, note, velocity in parse_ble_midi(bytes(data)):
            msg_type = status & 0xF0
            if msg_type == 0x90 and velocity > 0:
                print(f"  Note ON  — MIDI {note}  vel {velocity}")
                fs.noteon(CHANNEL, note, velocity)
            else:
                print(f"  Note OFF — MIDI {note}")
                fs.noteoff(CHANNEL, note)

    print(f"\nConnecting to BLE MIDI sender at {address}...")
    async with BleakClient(address) as client:
        await client.start_notify(BLE_MIDI_CHARACTERISTIC, on_midi)
        print("Listening for BLE MIDI. Play the LEGO instrument!\n")
        print("Ctrl-C to quit.\n")
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await client.stop_notify(BLE_MIDI_CHARACTERISTIC)

    fs.delete()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
