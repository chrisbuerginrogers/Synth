# UNO-Q Setup Guide

This guide documents the exact steps to set up the UNO Q as a standalone LEGO BLE MIDI
instrument, outputting audio to a Bluetooth speaker. No laptop required once set up.

**Hardware needed:**
- IK Multimedia UNO Q (4 GB Linux model)
- LEGO Education SPIKE Prime hub with Double Motor
- A Bluetooth speaker (tested with Bose Revolve SoundLink)
- A Mac or PC to run the initial setup (connected to the UNO Q via USB)

---

## 1. Connect to the UNO Q via ADB

The UNO Q exposes an ADB interface over USB. Install ADB on your Mac:

```bash
brew install --cask android-platform-tools
```

Plug the UNO Q into your Mac via USB, then verify it is detected:

```bash
adb devices
```

You should see one device listed. Forward SSH port (optional, for future use):

```bash
adb forward tcp:2222 tcp:22
```

Open a shell on the UNO Q:

```bash
adb shell
```

You will be logged in as `arduino`.

---

## 2. Activate the Python virtual environment

The UNO Q ships with a Python virtual environment at `~/lego-env`. Activate it with
`source` — do NOT run it directly:

```bash
source ~/lego-env/bin/activate
```

Your prompt will change to `(lego-env) arduino@...`.

> **Note:** The system `python3` and `pip` are not on the PATH. Always use
> `lego-env/bin/python3` directly, or activate the venv first.

---

## 3. Install Python dependencies

```bash
lego-env/bin/python3 -m pip install pyfluidsynth numpy legoeducation
```

---

## 4. Install FluidSynth system library

`pyfluidsynth` is just Python bindings — the system `libfluidsynth` is also needed.
Install it with sudo (use the `arduino` user password when prompted):

```bash
sudo apt-get install -y fluidsynth libfluidsynth-dev
```

---

## 5. Create the project folder and copy files

```bash
mkdir -p ~/Uno-Lego
mv ~/lego-env ~/Uno-Lego/
```

From your Mac, push the project files to the UNO Q:

```bash
adb push lelib.py /home/arduino/Uno-Lego/
adb push UNO-Q/uno_q_lego.py /home/arduino/Uno-Lego/
adb push GeneralUser_GS.sf2 /home/arduino/Uno-Lego/
```

---

## 6. Pair the Bluetooth speaker

The UNO Q uses BlueZ for Bluetooth. The speaker has two Bluetooth addresses:
- `LE-` prefixed address — BLE only, used for the Bose app. **Not for audio.**
- A plain address — Classic Bluetooth (BR/EDR), used for A2DP audio. **Use this one.**

Open `bluetoothctl` on the UNO Q:

```bash
bluetoothctl
```

Scan for Classic Bluetooth devices (not BLE):

```
scan bredr
```

Wait for your speaker to appear **without** the `LE-` prefix, note its MAC address,
then pair and trust it:

```
pair   AA:BB:CC:DD:EE:FF
trust  AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
quit
```

> **Tip:** If pairing fails with `AuthenticationFailed`, the speaker is not in pairing
> mode. Hold the Bluetooth button for 10 seconds until you hear "Bluetooth device list
> cleared", then retry.

> **Tip:** If connecting fails with `br-connection-busy`, the speaker is already
> connected to another device. Disconnect it from that device first.

---

## 7. Set up PipeWire audio routing

The UNO Q runs PipeWire under the `lightdm` user (uid 103). We need to make the
`arduino` user's audio route through lightdm's PipeWire session, which manages the
Bluetooth speaker.

### Start lightdm's PipeWire stack (if not already running)

```bash
sudo systemctl --machine=lightdm@ --user start pipewire.socket pipewire-pulse.socket wireplumber.service
sleep 5
```

### Connect the Bluetooth speaker

```bash
bluetoothctl connect AA:BB:CC:DD:EE:FF
```

### Make lightdm's PipeWire socket accessible to arduino

```bash
sudo chmod o+rx /run/user/103
sudo chmod o+rw /run/user/103/pipewire-0
```

### Verify the speaker is visible

```bash
XDG_RUNTIME_DIR=/run/user/103 pw-dump | grep -i bose
```

You should see `bluez_output.AA_BB_CC_DD_EE_FF.1` in the output.

### Test audio

```bash
XDG_RUNTIME_DIR=/run/user/103 pw-play --target bluez_output.AA_BB_CC_DD_EE_FF.1 /usr/share/sounds/alsa/Front_Left.wav
```

You should hear "Left" from the speaker.

---

## 8. Test FluidSynth audio

```bash
cd ~/Uno-Lego
```

Create and run a quick test:

```bash
lego-env/bin/python3 - << 'EOF'
import os
os.environ['PULSE_SERVER'] = 'unix:/run/user/103/pulse/native'
import fluidsynth, time
fs = fluidsynth.Synth()
fs.start(driver='pulseaudio')
sfid = fs.sfload('GeneralUser_GS.sf2')
fs.program_select(0, sfid, 0, 40)
print("You should hear a violin note...")
fs.noteon(0, 60, 100)
time.sleep(2)
fs.noteoff(0, 60)
fs.delete()
EOF
```

You should hear a violin note (middle C) from the Bluetooth speaker.

---

## 9. Run the instrument

Make sure the LEGO Double Motor is powered on and nearby, then:

```bash
cd ~/Uno-Lego
source lego-env/bin/activate
lego-env/bin/python3 uno_q_lego.py
```

**Playing:**
- Turn the **left motor** to select a note — the full rotation is divided into 5 zones:

  | Zone | Degrees | Note |
  |------|---------|------|
  | 1 | 0–71° | C |
  | 2 | 72–143° | D |
  | 3 | 144–215° | E |
  | 4 | 216–287° | F |
  | 5 | 288–359° | G |

- **Shake the hub** for 1 second to trigger the selected note.
- Press **Ctrl-C** to quit.

---

## Troubleshooting

### `No module named fluidsynth`
The venv python is not being used. Run with `lego-env/bin/python3` explicitly.

### `br-connection-profile-unavailable` when connecting speaker
PipeWire (with wireplumber) is not running. Run:
```bash
sudo systemctl --machine=lightdm@ --user start pipewire.socket pipewire-pulse.socket wireplumber.service
sleep 5
bluetoothctl connect AA:BB:CC:DD:EE:FF
```

### `br-connection-busy` when connecting speaker
The speaker is connected to another device. Disconnect it from that device first, or
clear the speaker's memory by holding the Bluetooth button for 10 seconds.

### No audio from speaker
Check that lightdm's PipeWire socket is accessible:
```bash
ls -la /run/user/103/pulse/native
```
If permission denied, re-run:
```bash
sudo chmod o+rx /run/user/103
sudo chmod o+rw /run/user/103/pipewire-0
```

### Speaker not found in `scan bredr`
Make sure the speaker is in pairing mode (not just powered on). Hold the Bluetooth
button until you hear the pairing prompt, then scan immediately.

---

## How it works

The `PULSE_SERVER` environment variable points FluidSynth's PulseAudio driver at
lightdm's PipeWire PulseAudio-compatible socket (`/run/user/103/pulse/native`).
PipeWire then routes the audio to the Bluetooth speaker over A2DP (Classic Bluetooth).
Meanwhile, the `legoeducation` SDK connects to the LEGO hardware over BLE — a separate
radio mode on the same Bluetooth chip, so there is no conflict.
