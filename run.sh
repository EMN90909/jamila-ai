#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"

echo "🌸 jamila-core installer — Accessible Voice Assistant"

# System dependencies (Debian/Ubuntu)
echo "📦 Installing system packages..."
sudo apt update || true
sudo apt install -y \
    python3-venv python3-dev build-essential \
    portaudio19-dev ffmpeg libasound-dev pv \
    xdotool pactl mpv wget curl \
    sox libsox-fmt-all || true

# Create virtual environment
if [ ! -d "$VENV" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv "$VENV"
fi

# Activate and install Python packages
source "$VENV/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

# Download Vosk offline model (small, ~50MB)
VOSK_MODEL="$ROOT/models/vosk-model-small-en-us-0.15"
if [ ! -d "$VOSK_MODEL" ]; then
    echo "📥 Downloading offline speech model (Vosk)..."
    mkdir -p "$ROOT/models"
    wget -q --show-progress -O "$ROOT/models/vosk-small-en-us.zip" \
        "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
    unzip -q "$ROOT/models/vosk-small-en-us.zip" -d "$ROOT/models"
    rm "$ROOT/models/vosk-small-en-us.zip"
    echo "✅ Vosk model ready: $VOSK_MODEL"
fi

# Setup credentials directory
mkdir -p "$ROOT/credentials"
touch "$ROOT/credentials/.gitkeep"

# Copy .env if missing
if [ ! -f "$ROOT/.env" ]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
    chmod 600 "$ROOT/.env"
    echo "⚠️  Copied .env.example → .env"
    echo "   ✏️  EDIT .env WITH YOUR API KEYS BEFORE FIRST RUN"
fi

echo ""
echo "✅ Installation complete!"
echo "───────────────────────────────"
echo "1. Edit .env with your API keys:"
echo "   nano $ROOT/.env"
echo ""
echo "2. Activate environment:"
echo "   source $VENV/bin/activate"
echo ""
echo "3. Run Jamila:"
echo "   python3 jamila_core.py"
echo ""
echo "🎧 Keybindings:"
echo "   SPACE = Toggle mic | ENTER = Execute | ESC = Cancel | CTRL+C = Quit"
echo "───────────────────────────────"
