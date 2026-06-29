# UNO-Q — Standalone LEGO BLE MIDI Instrument

Turns a LEGO SPIKE Prime hub and an IK Multimedia UNO Q (4 GB Linux model) into a
self-contained musical instrument with no laptop required.

```
LEGO hub (MicroPython)          UNO Q (Linux)              BLE Speaker
┌─────────────────────┐        ┌──────────────────────┐   ┌──────────┐
│ lego_instrument.py  │        │ uno_q_synth.py        │   │          │
│                     │        │                       │   │          │
│ motor A → note      │─BLE───▶│ FluidSynth            │──▶│  audio   │
│ shake   → trigger   │  MIDI  │ PulseAudio → BlueZ    │   │          │
└─────────────────────┘        └──────────────────────┘   └──────────┘
```

The LEGO hub advertises itself as a BLE MIDI peripheral. The UNO Q connects to it,
receives MIDI note-on/off packets, renders them through FluidSynth, and streams the
audio to a paired Bluetooth speaker over A2DP.

---

## Architectures

### Simplest — everything on the UNO Q (recommended)

Requires `pip install legoeducation` to work on the UNO Q's Linux ARM.

```
LEGO hardware ──BLE──▶ UNO Q (uno_q_lego.py) ──A2DP──▶ BLE speaker
```

The UNO Q connects to LEGO hardware over BLE (low-energy side of its Bluetooth radio)
and streams audio to the speaker over Classic Bluetooth A2DP (BR/EDR side) —
two different radio modes, one chip, no conflict.

### Fallback — PC in the middle (if legoeducation won't install on UNO Q)

```
LEGO hardware ──BLE──▶ PC (lego_ble_midi.py) ──BLE MIDI──▶ UNO Q (uno_q_synth.py) ──A2DP──▶ BLE speaker
```

The PC handles the LEGO SDK and translates motor/shake events into BLE MIDI packets.
The UNO Q receives MIDI and does synthesis only.

---

## Files

| File | Where it runs | Purpose |
|------|--------------|---------|
| `uno_q_lego.py` | UNO Q | **Recommended** — connects to LEGO over BLE, plays via FluidSynth → BLE speaker |
| `uno_q_synth.py` | UNO Q | Fallback — receives BLE MIDI from PC, plays via FluidSynth → BLE speaker |
| `uno_q_setup.sh` | UNO Q (run once) | Installs all dependencies, pairs BLE speaker |
| `uno_q.py` | Mac | Simple FluidSynth driver for UNO Q as a USB MIDI keyboard |
| `lego_ble_midi.py` | Mac | Sends BLE MIDI from LEGO hardware (fallback path only) |

> `lego_instrument.py` (SPIKE Prime MicroPython) lives in `SPIKE_Prime/BLE/` alongside
> `BLE_CEEO.py` and `BLE_MIDI.py`. Only needed for the SPIKE Prime hub path.

---

## How it works

### Playing the instrument

- **Turn motor A** on the LEGO hub to select a note. The motor's full 360° rotation
  is divided into five zones of 72° each, mapped to C D E F G (octave 4).
- **Shake the hub** to trigger the selected note. The accelerometer variance over the
  last second is checked — sustained shaking fires a note-on, holds it for 0.5 s,
  then sends note-off.

### BLE MIDI

The LEGO hub runs MicroPython and uses the `bluetooth` module to act as a BLE MIDI
**peripheral** — it advertises the standard BLE MIDI service UUID
(`03B80E5A-EDE8-4B33-A751-6CE34EC4C700`) and sends note packets using the format
defined in the BLE MIDI spec (5-byte packets with a 13-bit millisecond timestamp).

The UNO Q acts as the BLE MIDI **central** — it scans for a device named `LegoSynth`,
connects, and subscribes to notifications on the MIDI characteristic.

### FluidSynth on the UNO Q

FluidSynth is a software synthesizer that renders MIDI events using sampled instrument
recordings stored in a SoundFont file (`GeneralUser_GS.sf2`). On the UNO Q it outputs
audio to PulseAudio, which routes it to the paired Bluetooth speaker via BlueZ A2DP.

---

## Setup

### Step 1 — UNO Q (run once)

SSH into the UNO Q and run the setup script:

```bash
chmod +x uno_q_setup.sh
./uno_q_setup.sh
```

This installs: `fluidsynth`, `python3-pyfluidsynth`, `pulseaudio`,
`pulseaudio-module-bluetooth`, `bluez`, and the `bleak` Python package.
It also downloads the GeneralUser GS soundfont if it is not already present.

### Step 2 — Pair the BLE speaker

Run the setup script with your speaker's MAC address (find it from `bluetoothctl scan on`):

```bash
./uno_q_setup.sh --pair AA:BB:CC:DD:EE:FF
```

Or pair manually:

```bash
bluetoothctl
> power on
> agent on
> scan on          # note your speaker's MAC address
> pair   AA:BB:CC:DD:EE:FF
> trust  AA:BB:CC:DD:EE:FF
> connect AA:BB:CC:DD:EE:FF
> quit
```

Then set it as the default audio output:

```bash
pactl set-default-sink bluez_sink.AA_BB_CC_DD_EE_FF.a2dp_sink
```

### Step 3 — Deploy to the LEGO hub

Copy three files to the hub using the SPIKE app or `spike-tools`:

```
SPIKE_Prime/BLE/BLE_CEEO.py
SPIKE_Prime/BLE/BLE_MIDI.py
SPIKE_Prime/BLE/lego_instrument.py
```

### Step 4 — Run

**Recommended (everything on UNO Q):**

```bash
pip3 install legoeducation numpy
python3 uno_q_lego.py
```

The UNO Q connects to the LEGO hardware over BLE and plays audio to the BLE speaker.
No PC needed.

**Fallback (PC in the middle):**

On the PC:
```bash
python3 lego_ble_midi.py
```

On the UNO Q:
```bash
python3 uno_q_synth.py
```

---

## Configuration

### Change the instrument (UNO Q)

Edit `uno_q_synth.py` and change `PROGRAM` to any General MIDI program number:

```python
PROGRAM = 40   # 40 = Violin, 0 = Piano, 56 = Trumpet
```

### Change the instrument (hub)

Edit `lego_instrument.py` and change `INSTRUMENT` to any key from the `instruments`
dict in `BLE_MIDI.py`:

```python
INSTRUMENT = 'Violin'   # 'Trumpet', 'Flute', 'Acoustic Grand Piano', etc.
```

### Change the notes

Edit `NOTE_NAMES` and `NOTE_MIDI` in `lego_instrument.py` to use a different scale,
more notes, or a different octave:

```python
NOTE_NAMES = ['C', 'D', 'E', 'F', 'G']
NOTE_MIDI  = {'C': 60, 'D': 62, 'E': 64, 'F': 65, 'G': 67}  # octave 4
```

---

## Laptop mode (testing without the UNO Q)

Two scripts let you test individual pieces on a Mac:

**Test the UNO Q as a plain USB MIDI keyboard:**

```bash
python3 uno_q.py
```

Starts FluidSynth with CoreAudio + CoreMIDI so the UNO Q keyboard plays directly
through the Mac speakers.

**Test the LEGO hub → BLE MIDI path from a Mac:**

```bash
pip install bleak numpy
python3 lego_ble_midi.py
```

Connects to the LEGO hub via the `legoeducation` SDK and sends BLE MIDI to whatever
central is listening (the UNO Q or any BLE MIDI app).

---

## Dependencies

### LEGO hub (MicroPython — built in)
- `bluetooth` — BLE peripheral
- `motor`, `motion_sensor`, `hub.port` — hardware access
- `BLE_CEEO.py`, `BLE_MIDI.py` — CEEO BLE MIDI library (already in `SPIKE_Prime/BLE/`)

### UNO Q (install via `uno_q_setup.sh`)
- `fluidsynth` — software synthesizer
- `python3-pyfluidsynth` — Python bindings
- `pulseaudio` + `pulseaudio-module-bluetooth` — audio routing
- `bluez` — Bluetooth stack
- `bleak` — BLE MIDI client (Python)

### Mac / laptop mode only
- `bleak` — BLE MIDI sender
- `legoeducation` — LEGO hub SDK
- `numpy` — accelerometer variance calculation
