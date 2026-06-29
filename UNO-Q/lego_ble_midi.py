"""
lego_ble_midi.py  —  runs on the Mac (or any Python host attached to the LEGO hub)

Reads the LEGO Double Motor (position → note, shake → trigger) and broadcasts
BLE MIDI note-on / note-off packets so the UNO Q (or any BLE MIDI receiver)
can pick them up and play them through FluidSynth.

Dependencies:
    pip install bleak numpy
    pip install legoeducation   # LEGO Education Python SDK

Usage:
    python3 lego_ble_midi.py
"""

import asyncio
import math
import time
import struct
import numpy as np
from lelib import doubleMotor

# ── LEGO config ───────────────────────────────────────────────────────────────

SERIAL = 27   # card serial 0027

NOTE_NAMES = ['C', 'D', 'E', 'F', 'G']
NOTE_MIDI  = {'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67}

SHAKE_VARIANCE_THRESHOLD = 400_000   # (mg)²
SHAKE_WINDOW_SECS        = 1.0
POLL_HZ                  = 20
POLL_INTERVAL            = 1.0 / POLL_HZ

MIDI_CHANNEL  = 0    # 0-indexed → MIDI channel 1
NOTE_VELOCITY = 100
NOTE_DURATION = 0.5  # seconds

# ── BLE MIDI UUIDs (standard, works with any BLE MIDI peripheral) ─────────────

BLE_MIDI_SERVICE       = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"
BLE_MIDI_CHARACTERISTIC = "7772e5db-3868-4112-a1a9-f2669d106bf3"

# ── BLE MIDI packet helpers ───────────────────────────────────────────────────
# Format: [header, timestamp, status, note, velocity]
# header:    0x80 | (timestamp_high & 0x3F)
# timestamp: 0x80 | (timestamp_low  & 0x7F)

def _ble_midi_packet(status, note, velocity):
    ts = int(time.time() * 1000) & 0x1FFF   # 13-bit millisecond timestamp
    header = 0x80 | ((ts >> 7) & 0x3F)
    stamp  = 0x80 | (ts & 0x7F)
    return bytes([header, stamp, status, note, velocity])

def note_on_packet(note, velocity=NOTE_VELOCITY, channel=MIDI_CHANNEL):
    return _ble_midi_packet(0x90 | (channel & 0x0F), note & 0x7F, velocity & 0x7F)

def note_off_packet(note, channel=MIDI_CHANNEL):
    return _ble_midi_packet(0x80 | (channel & 0x0F), note & 0x7F, 0)

# ── Note selection ────────────────────────────────────────────────────────────

def motor_pos_to_note(abs_pos):
    zone = int(abs_pos / 72) % 5
    return NOTE_NAMES[zone]

# ── BLE scan: find the UNO Q (or any BLE MIDI device) ────────────────────────

async def find_ble_midi_device():
    from bleak import BleakScanner
    print("Scanning for BLE MIDI devices (10 s)...")
    devices = await BleakScanner.discover(timeout=10.0, service_uuids=[BLE_MIDI_SERVICE])
    if not devices:
        raise RuntimeError("No BLE MIDI device found. Is the UNO Q powered on and in BLE MIDI mode?")
    # prefer a device whose name contains "UNO"
    for d in devices:
        if d.name and "UNO" in d.name.upper():
            print(f"Found UNO Q: {d.name} ({d.address})")
            return d.address
    d = devices[0]
    print(f"Found BLE MIDI device: {d.name} ({d.address})")
    return d.address

# ── Shake detection ───────────────────────────────────────────────────────────

def _accel_magnitude(dm):
    imu = dm.imu_device
    return math.sqrt(imu.accelerometerX**2 + imu.accelerometerY**2 + imu.accelerometerZ**2)

# ── Main ──────────────────────────────────────────────────────────────────────

async def run():
    from bleak import BleakClient

    address = await find_ble_midi_device()

    dm = doubleMotor()
    print(f"Connecting to LEGO Double Motor (serial {SERIAL:04d})...")
    dm.connect(card_serial=SERIAL)
    print("Connected.\n")
    print("Turn the left motor to select a note (C D E F G), shake to play.")
    print("Zones: C=0-71°  D=72-143°  E=144-215°  F=216-287°  G=288-359°\n")

    async with BleakClient(address) as client:
        print(f"Connected to BLE MIDI device at {address}\n")

        mag_window = []
        last_note  = None
        playing    = False

        while True:
            loop_start = time.time()

            abs_pos = dm.motor[0].absolutePosition
            note    = motor_pos_to_note(abs_pos)
            midi    = NOTE_MIDI[note]

            if note != last_note:
                print(f"  Motor {abs_pos:3d}°  →  {note}4  (MIDI {midi})")
                last_note = note

            mag = _accel_magnitude(dm)
            now = time.time()
            mag_window.append((now, mag))
            mag_window = [(t, m) for t, m in mag_window if now - t <= SHAKE_WINDOW_SECS]

            min_samples = int(SHAKE_WINDOW_SECS * POLL_HZ * 0.8)
            if not playing and len(mag_window) >= min_samples:
                variance = float(np.var([m for _, m in mag_window]))
                if variance > SHAKE_VARIANCE_THRESHOLD:
                    print(f"  Shake!  Sending {note}4 over BLE MIDI...")
                    playing = True

                    await client.write_gatt_char(
                        BLE_MIDI_CHARACTERISTIC,
                        note_on_packet(midi),
                        response=False,
                    )
                    await asyncio.sleep(NOTE_DURATION)
                    await client.write_gatt_char(
                        BLE_MIDI_CHARACTERISTIC,
                        note_off_packet(midi),
                        response=False,
                    )

                    playing = False
                    mag_window.clear()
                    print()

            elapsed = time.time() - loop_start
            await asyncio.sleep(max(0, POLL_INTERVAL - elapsed))

if __name__ == "__main__":
    asyncio.run(run())
