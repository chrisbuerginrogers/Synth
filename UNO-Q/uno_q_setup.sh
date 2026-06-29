#!/usr/bin/env bash
# uno_q_setup.sh — run once on the UNO Q to install dependencies
# and (optionally) pair a BLE speaker.
#
# Usage:
#   chmod +x uno_q_setup.sh
#   ./uno_q_setup.sh
#   ./uno_q_setup.sh --pair AA:BB:CC:DD:EE:FF   # also pair a specific speaker MAC

set -e

echo "=== UNO Q FluidSynth + BLE speaker setup ==="

# ── System packages ────────────────────────────────────────────────────────────
echo "[1/4] Installing system packages..."
apt-get update -q
apt-get install -y -q \
    fluidsynth \
    python3-pyfluidsynth \
    pulseaudio \
    pulseaudio-module-bluetooth \
    bluez \
    python3-pip

# ── Python packages ───────────────────────────────────────────────────────────
echo "[2/4] Installing Python packages..."
pip3 install --quiet bleak

# ── PulseAudio Bluetooth module ───────────────────────────────────────────────
echo "[3/4] Enabling PulseAudio Bluetooth module..."
if ! grep -q "module-bluetooth-policy" /etc/pulse/default.pa 2>/dev/null; then
    echo "load-module module-bluetooth-policy" >> /etc/pulse/default.pa
    echo "load-module module-bluetooth-discover" >> /etc/pulse/default.pa
fi

# ── Soundfont ─────────────────────────────────────────────────────────────────
SFDIR="$(dirname "$0")"
if [ ! -f "$SFDIR/GeneralUser_GS.sf2" ]; then
    echo "[4/4] Downloading GeneralUser GS soundfont (~30 MB)..."
    curl -L -o "$SFDIR/GeneralUser_GS.sf2" \
        "https://www.generaluser.us/files/GeneralUser_GS_v1.471.zip" 2>/dev/null || \
    wget -q -O /tmp/gu.zip \
        "https://www.generaluser.us/files/GeneralUser_GS_v1.471.zip" && \
        unzip -p /tmp/gu.zip "*.sf2" > "$SFDIR/GeneralUser_GS.sf2"
    echo "    Soundfont saved to $SFDIR/GeneralUser_GS.sf2"
else
    echo "[4/4] Soundfont already present, skipping download."
fi

# ── Optional: pair a BLE speaker ─────────────────────────────────────────────
if [ "$1" = "--pair" ] && [ -n "$2" ]; then
    SPEAKER_MAC="$2"
    echo ""
    echo "=== Pairing BLE speaker $SPEAKER_MAC ==="
    bluetoothctl <<EOF
power on
agent on
default-agent
scan on
EOF
    sleep 5
    bluetoothctl <<EOF
pair $SPEAKER_MAC
trust $SPEAKER_MAC
connect $SPEAKER_MAC
EOF
    echo ""
    echo "Setting BLE speaker as default PulseAudio sink..."
    # convert MAC AA:BB:CC:DD:EE:FF → bluez_sink.AA_BB_CC_DD_EE_FF.a2dp_sink
    SINK="bluez_sink.$(echo "$SPEAKER_MAC" | tr ':' '_').a2dp_sink"
    pactl set-default-sink "$SINK" || echo "  (Sink not yet visible — run after speaker is connected)"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "To run the synth:"
echo "    python3 uno_q_synth.py"
echo ""
echo "To pair a BLE speaker later:"
echo "    $0 --pair AA:BB:CC:DD:EE:FF"
echo ""
echo "To change the default audio output to your BLE speaker:"
echo "    pactl set-default-sink bluez_sink.AA_BB_CC_DD_EE_FF.a2dp_sink"
