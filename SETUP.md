# Synth — Student Setup Guide

Two Python scripts are included. Both play a C major scale and chord using synthesized violin and trumpet sounds. They differ in how they produce audio:

| Script | Approach | Install complexity |
|---|---|---|
| `synth.py` | FluidSynth — realistic soundfont samples | Requires a system library |
| `synth_pygame.py` | Additive synthesis — builds timbres from harmonics | pip only |

**Start with `synth_pygame.py`** — it is easier to install on all platforms.

---

## Prerequisites

- Python 3.14 — download from [python.org](https://python.org)
- A terminal (Terminal on Mac, Command Prompt or PowerShell on Windows)

Verify your Python version:

```
python3.14 --version
```

---

## 1. Create a virtual environment

A virtual environment keeps the packages for this project separate from the rest of your system.

Navigate to the project folder in your terminal, then run:

**Mac / Linux**
```
python3.14 -m venv .venv
```

**Windows**
```
py -3.14 -m venv .venv
```

---

## 2. Activate the virtual environment

You need to activate the environment every time you open a new terminal session.

**Mac / Linux**
```
source .venv/bin/activate
```

**Windows**
```
.venv\Scripts\activate
```

Your terminal prompt will show `(.venv)` when it is active.

---

## 3. Install dependencies

### For `synth_pygame.py` (recommended — pip only)

```
pip install sounddevice numpy
```

That is all. Skip ahead to **Running the scripts**.

---

### For `synth.py` (FluidSynth version)

This script uses real instrument samples stored in a soundfont file. It requires the FluidSynth C library to be installed on your system before the Python package.

**Mac**
```
brew install fluid-synth
pip install pyfluidsynth numpy
```

**Windows**

1. Download the latest FluidSynth release from github.com/FluidSynth/fluidsynth/releases — get the `.zip` for Windows.
2. Extract it and copy `libfluidsynth-3.dll` into the same folder as `synth.py`.
3. Download a free soundfont such as **GeneralUser GS** (search "GeneralUser GS sf2 download") and place the `.sf2` file in the same folder.
4. Update the `SOUNDFONTS["Windows"]` path in `synth.py` to match your `.sf2` filename.
5. Then install the Python package:

```
pip install pyfluidsynth numpy
```

**Linux**
```
sudo apt install fluidsynth          # Ubuntu / Debian
sudo dnf install fluidsynth          # Fedora
pip install pyfluidsynth numpy
```

---

## 4. Open in VS Code

VS Code will automatically use the `.venv` Python interpreter if you open the project folder directly:

```
code .
```

If it does not pick it up automatically, press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows), type **Python: Select Interpreter**, and choose the one that shows `.venv`.

---

## 5. Run the scripts

Make sure your virtual environment is active (step 2), then:

```
python synth_pygame.py
```

or

```
python synth.py
```

You should hear a C major scale followed by a C major chord played by a violin and trumpet together.

---

## What the code does

### `synth_pygame.py` — additive synthesis

Each instrument is defined by a list of harmonics — pairs of `(harmonic number, amplitude)`:

```python
VIOLIN_HARMONICS  = [(1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.2), (6, 0.1)]
TRUMPET_HARMONICS = [(1, 1.0), (2, 0.9), (3, 0.8), (4, 0.7), (5, 0.5), (6, 0.3), (7, 0.2)]
```

The `synthesize` function builds a sound wave by adding up sine waves at each harmonic frequency. This is the basis of **Fourier synthesis** — any sound can be approximated by summing enough sine waves. Try changing the amplitudes and re-running to hear how the timbre changes.

### `synth.py` — soundfont synthesis (FluidSynth)

Uses **General MIDI** instrument numbers to select instruments:

- Channel 0 → Program 40 → Violin
- Channel 1 → Program 56 → Trumpet

MIDI note numbers follow the formula: middle C (C4) = 60, each semitone up or down adds or subtracts 1.

---

## Troubleshooting

**`command not found: python3.14`**
Python 3.14 is not installed or not on your PATH. Download it from python.org.

**`(.venv)` is not showing in my terminal**
You have not activated the environment. Run the activate command from step 2.

**`No module named sounddevice`**
The package is not installed in your active environment. Make sure `(.venv)` is showing, then run `pip install sounddevice numpy`.

**No sound on Mac**
macOS may ask for microphone/audio permissions the first time. Check System Settings → Privacy & Security → Microphone.

**No sound on Windows (FluidSynth)**
Make sure `libfluidsynth-3.dll` is in the same folder as `synth.py` and that the soundfont path in the script matches your `.sf2` filename.
