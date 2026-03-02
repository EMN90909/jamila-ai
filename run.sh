#!/usr/bin/env bash
# ╔════════════════════════════════════════════════════════╗
# ║   JAMILA AI INSTALLER v2.0 (KEY-FREE)                 ║
# ║   Voice-First AI for Linux                             ║
# ╚════════════════════════════════════════════════════════╝
set -e

INSTALL_DIR="$HOME/.jamila"
VENV="$INSTALL_DIR/.venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║   JAMILA AI INSTALLER v2.0 (KEY-FREE)             ║"
echo "║   Voice-First AI for Linux                        ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# ─── STEP 1: System packages ───────────────────────────
echo "→ Installing system packages..."
echo "  (This may ask for your sudo password)"

if command -v apt-get &>/dev/null; then
  sudo apt-get update -qq 2>/dev/null || true
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-venv python3-dev python3-pip \
    build-essential cmake pkg-config \
    portaudio19-dev libportaudio2 \
    ffmpeg libavcodec-dev libavformat-dev \
    xdotool mpv \
    espeak-ng libespeak-ng-dev \
    python3-tk python3-gi python3-gi-cairo \
    gir1.2-gtk-3.0 libgtk-3-dev \
    libgirepository1.0-dev \
    wget curl git \
    2>/dev/null || echo "⚠ Some packages may not have installed (continuing anyway)"
elif command -v dnf &>/dev/null; then
  sudo dnf install -y python3 python3-venv python3-devel gcc cmake \
    portaudio-devel ffmpeg xdotool mpv espeak-ng gtk3-devel \
    gobject-introspection-devel python3-gobject 2>/dev/null || true
elif command -v pacman &>/dev/null; then
  sudo pacman -S --noconfirm python python-virtualenv base-devel cmake \
    portaudio ffmpeg xdotool mpv espeak-ng gtk3 \
    python-gobject gobject-introspection 2>/dev/null || true
else
  echo "⚠ Unknown package manager. Please manually install: python3, portaudio, ffmpeg, espeak-ng, gtk3"
fi

# ─── STEP 2: Setup directory ──────────────────────────
echo ""
echo "→ Setting up Jamila directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/modules"

# ─── STEP 3: Copy source files ────────────────────────
echo "→ Copying Jamila files..."
cp "$SCRIPT_DIR/jamila_core.py" "$INSTALL_DIR/jamila_core.py"

if [ -d "$SCRIPT_DIR/modules" ]; then
  cp -r "$SCRIPT_DIR/modules/"* "$INSTALL_DIR/modules/"
fi

if [ -f "$SCRIPT_DIR/jamila.png" ]; then
  cp "$SCRIPT_DIR/jamila.png" "$INSTALL_DIR/jamila.png"
  echo "  ✓ Jamila icon installed"
fi

touch "$INSTALL_DIR/modules/__init__.py"

# ─── STEP 4: Python virtual environment ───────────────
echo ""
echo "→ Creating Python virtual environment..."
if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

echo "→ Upgrading pip..."
pip install --upgrade pip -q

echo "→ Installing base Python packages..."
pip install -q \
  requests \
  SpeechRecognition \
  pillow \
  2>/dev/null || true

echo "→ Installing PyAudio (microphone support)..."
pip install -q pyaudio 2>/dev/null || \
  pip install -q --no-build-isolation pyaudio 2>/dev/null || \
  echo "  ⚠ PyAudio failed (voice input may not work, text input still works)"

echo "→ Installing Coqui TTS..."
pip install -q TTS 2>/dev/null && echo "✓ Coqui TTS installed!" || {
  echo "  ⚠ Full Coqui TTS failed, trying minimal install..."
  pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || true
  pip install -q TTS 2>/dev/null || echo "  ⚠ Coqui TTS failed, will use espeak-ng instead"
}
pip install -q soundfile sounddevice pyttsx3 2>/dev/null || true

echo ""
echo "✓ Python packages installed"

# ─── STEP 5: Create launcher ─────────────────────────
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/jamila" << LAUNCHEOF
#!/usr/bin/env bash
source "$VENV/bin/activate"
python3 "$INSTALL_DIR/jamila_core.py" "\$@"
LAUNCHEOF
chmod +x "$HOME/.local/bin/jamila"

if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
  SHELL_RC=""
  [ -f "$HOME/.bashrc" ] && SHELL_RC="$HOME/.bashrc"
  [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
  if [ -n "$SHELL_RC" ]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "  Added ~/.local/bin to PATH in $SHELL_RC"
  fi
fi

sudo ln -sf "$HOME/.local/bin/jamila" /usr/local/bin/jamila 2>/dev/null || true

# ─── DONE ────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║  ✓ Jamila is installed! (no activation needed)    ║"
echo "║  Run:  jamila                                     ║"
echo "╚════════════════════════════════════════════════════╝"
