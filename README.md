# Synth

Three Python scripts that synthesize and play a C major scale and chord using violin and trumpet sounds. Each script uses a different synthesis technique, making them useful as a progression from simple to advanced.

| Script | Technique | Dependencies |
|---|---|---|
| `synth_pygame.py` | Additive synthesis | `pip` only |
| `synth_advanced.py` | Karplus-Strong + FM synthesis | `pip` only |
| `synth.py` | SoundFont playback via FluidSynth | Requires a system library |

**Start with `synth_pygame.py`** — it installs on all platforms with a single `pip` command.

---

## How the synthesis works

### `synth_pygame.py` — additive synthesis

Builds each instrument by summing sine waves at harmonic multiples of the fundamental frequency. The mix of harmonics and their amplitudes determines the timbre — a violin sounds different from a trumpet because it emphasises different harmonics. This is the basis of **Fourier synthesis**.

### `synth_advanced.py` — Karplus-Strong + FM synthesis

Uses two more physically motivated algorithms:

- **Karplus-Strong** (string): fills a circular buffer with noise, then repeatedly averages adjacent samples. The low-pass filtering smooths the noise into a decaying pitched tone that mimics a plucked or bowed string.
- **FM synthesis** (brass): modulates a carrier sine wave's frequency with a second sine wave. A high modulation index creates many sidebands and a bright, brassy attack; letting the index decay over time produces the warm sustain characteristic of a trumpet.

### `synth.py` — SoundFont / FluidSynth

Drives the FluidSynth C library with real sampled instrument recordings stored in `GeneralUser_GS.sf2`. Selects instruments by General MIDI program number (40 = Violin, 56 = Trumpet) and triggers notes by MIDI note number (middle C = 60).

---

## UNO-Q — Standalone BLE MIDI Instrument

See [`UNO-Q/`](UNO-Q/) for a self-contained system that turns a LEGO SPIKE Prime hub
and an IK Multimedia UNO Q into a wireless instrument with no laptop required.

---

## Setup

See [SETUP.md](SETUP.md) for full installation instructions across Mac, Windows, and Linux.

**Quick start (Mac/Linux):**

```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install sounddevice numpy
python synth_pygame.py
```
