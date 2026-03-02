#!/usr/bin/env bash
# ╔════════════════════════════════════════════════════════╗
# ║   JAMILA AI INSTALLER v2.0                            ║
# ║   Voice-First AI for Blind Linux Users               ║
# ║   github.com/EMN90909/jamila                         ║
# ╚════════════════════════════════════════════════════════╝
set -e

JAMILA_SERVER="https://jamila.onrender.com"
INSTALL_DIR="$HOME/.jamila"
KEY_FILE="$INSTALL_DIR/.jamila_key"
VENV="$INSTALL_DIR/.venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║   JAMILA AI INSTALLER v2.0                        ║"
echo "║   Voice-First AI for Linux                        ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# ─── STEP 1: Activation Key ──────────────────────────────────────────────────
JAMILA_KEY=""

if [ -f "$KEY_FILE" ]; then
  EXISTING=$(cat "$KEY_FILE" | tr -d '[:space:]')
  echo "→ Checking saved key..."
  VERIFY=$(curl -sf --max-time 10 -X POST "$JAMILA_SERVER/api/verify-key" \
    -H "Content-Type: application/json" \
    -d "{\"key\":\"$EXISTING\"}" 2>/dev/null || echo '{"valid":false}')
  VALID=$(echo "$VERIFY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('valid',False))" 2>/dev/null || echo "False")
  if [ "$VALID" = "True" ]; then
    PLAN=$(echo "$VERIFY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('plan','free'))" 2>/dev/null || echo "free")
    echo "✓ Saved key is valid. Plan: $PLAN"
    JAMILA_KEY="$EXISTING"
  else
    echo "⚠ Saved key is no longer valid."
  fi
fi

if [ -z "$JAMILA_KEY" ]; then
  echo ""
  echo "┌────────────────────────────────────────────────────┐"
  echo "│  Get your activation key at:                      │"
  echo "│  https://jamila.onrender.com                      │"
  echo "│  Sign up (free trial available) then copy your key│"
  echo "└────────────────────────────────────────────────────┘"
  echo ""
  read -rp "Enter your Jamila activation key: " JAMILA_KEY
  JAMILA_KEY=$(echo "$JAMILA_KEY" | tr -d '[:space:]')

  if [ -z "$JAMILA_KEY" ]; then
    echo "❌ No key entered. Exiting."
    exit 1
  fi

  echo "→ Verifying key with server..."
  VERIFY=$(curl -sf --max-time 12 -X POST "$JAMILA_SERVER/api/verify-key" \
    -H "Content-Type: application/json" \
    -d "{\"key\":\"$JAMILA_KEY\"}" 2>/dev/null || echo '{"valid":false,"reason":"Cannot reach server - check internet"}')

  VALID=$(echo "$VERIFY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('valid',False))" 2>/dev/null || echo "False")

  if [ "$VALID" != "True" ]; then
    REASON=$(echo "$VERIFY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('reason','Invalid key'))" 2>/dev/null || echo "Invalid key")
    echo ""
    echo "❌ Key rejected: $REASON"
    echo "   Visit $JAMILA_SERVER to get a valid key."
    exit 1
  fi

  PLAN=$(echo "$VERIFY" | python3 -c "import sys,json;print(json.load(sys.stdin).get('plan','free'))" 2>/dev/null || echo "free")
  echo ""
  echo "✓ Key verified! Plan: $PLAN"
fi

# ─── STEP 2: System packages ─────────────────────────────────────────────────
echo ""
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
  echo "✓ System packages installed"

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

# ─── STEP 3: Setup directory ─────────────────────────────────────────────────
echo ""
echo "→ Setting up Jamila directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/modules"

# ─── STEP 4: Copy source files ───────────────────────────────────────────────
echo "→ Copying Jamila files..."

# Copy main script
cp "$SCRIPT_DIR/jamila_core.py" "$INSTALL_DIR/jamila_core.py"

# Copy modules
if [ -d "$SCRIPT_DIR/modules" ]; then
  cp -r "$SCRIPT_DIR/modules/"* "$INSTALL_DIR/modules/"
fi

# Copy icon (jamila.png should be in repo)
if [ -f "$SCRIPT_DIR/jamila.png" ]; then
  cp "$SCRIPT_DIR/jamila.png" "$INSTALL_DIR/jamila.png"
  echo "  ✓ Jamila icon installed"
fi

# Create modules/__init__.py
touch "$INSTALL_DIR/modules/__init__.py"

# Write search_ui.py if not present
if [ ! -f "$INSTALL_DIR/modules/search_ui.py" ]; then
cat > "$INSTALL_DIR/modules/search_ui.py" << 'SEARCHEOF'
import threading, webbrowser, requests
try:
    from tkinter import Tk, Listbox, Scrollbar, END, SINGLE
    HAS_TK = True
except ImportError:
    HAS_TK = False

DUCK = 'https://api.duckduckgo.com/'

def ddg_instant(query):
    try:
        r = requests.get(DUCK, params={'q': query, 'format': 'json', 'no_html': 1}, timeout=6)
        j = r.json()
        results = []
        if j.get('AbstractText'):
            results.append((j.get('AbstractText'), j.get('AbstractURL')))
        for t in j.get('RelatedTopics', []):
            if isinstance(t, dict) and t.get('FirstURL'):
                results.append((t.get('Text') or t.get('Name'), t.get('FirstURL')))
        if not results:
            results.append((f'Open DuckDuckGo search for {query}', f'https://duckduckgo.com/?q={query}'))
        return results
    except Exception:
        return [(f'Open search for {query}', f'https://duckduckgo.com/?q={query}')]

class SearchBox:
    def __init__(self, query):
        self.query = query
        self.results = ddg_instant(query)
        if HAS_TK:
            t = threading.Thread(target=self._show); t.daemon = True; t.start()
        else:
            for i,(text,url) in enumerate(self.results[:5]):
                print(f"  {i+1}. {text[:100]}")
                print(f"     {url}")

    def _show(self):
        root = Tk(); root.title('Jamila Search')
        lb = Listbox(root, selectmode=SINGLE, width=80, height=20)
        lb.pack(side='left', fill='both', expand=True)
        sb = Scrollbar(root); sb.pack(side='right', fill='y')
        lb.config(yscrollcommand=sb.set); sb.config(command=lb.yview)
        for i,(t,url) in enumerate(self.results):
            lb.insert(END, f"{i+1}. {t[:120]}")
        def on_open(evt=None):
            sel = lb.curselection()
            if sel: webbrowser.open(self.results[sel[0]][1])
        lb.bind('<Double-Button-1>', on_open); root.mainloop()
SEARCHEOF
fi

echo "✓ Source files installed"

# ─── STEP 5: Python virtual environment ──────────────────────────────────────
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

# pyaudio can be tricky
echo "→ Installing PyAudio (microphone support)..."
pip install -q pyaudio 2>/dev/null || \
  pip install -q --no-build-isolation pyaudio 2>/dev/null || \
  echo "  ⚠ PyAudio failed (voice input may not work, text input still works)"

# ── COQUI TTS ──────────────────────────────────────────────────────────────
echo ""
echo "→ Installing Coqui TTS neural voice engine..."
echo "  (This is ~200MB and may take a few minutes on slow connections)"
echo "  Coqui gives Jamila a natural, warm voice instead of robotic speech."
echo ""

pip install -q TTS 2>/dev/null && echo "✓ Coqui TTS installed!" || {
  echo "  ⚠ Full Coqui TTS failed, trying minimal install..."
  pip install -q \
    torch torchaudio --index-url https://download.pytorch.org/whl/cpu 2>/dev/null || true
  pip install -q TTS 2>/dev/null || {
    echo "  ⚠ Coqui TTS could not be installed."
    echo "  Jamila will use espeak-ng instead (less natural voice)."
    echo "  To install manually later: pip install TTS"
  }
}

# Install soundfile and sounddevice for Coqui audio playback
pip install -q soundfile sounddevice 2>/dev/null || true

# pyttsx3 as last resort TTS
pip install -q pyttsx3 2>/dev/null || true

echo ""
echo "✓ Python packages installed"

# ─── STEP 6: Save key ────────────────────────────────────────────────────────
echo "$JAMILA_KEY" > "$KEY_FILE"
chmod 600 "$KEY_FILE"
echo "✓ Activation key saved"

# ─── STEP 7: Pre-download Coqui TTS model (optional but nice) ───────────────
echo ""
echo "→ Pre-loading Coqui TTS voice model (first-time only)..."
source "$VENV/bin/activate"
python3 -c "
try:
    from TTS.api import TTS
    print('  Downloading voice model...')
    tts = TTS(model_name='tts_models/en/ljspeech/tacotron2-DDC', progress_bar=True, gpu=False)
    print('  ✓ Voice model ready')
except Exception as e:
    print(f'  ⚠ Could not pre-load voice model: {e}')
    print('  It will load on first run instead.')
" 2>/dev/null || echo "  (Voice model will load on first run)"

# ─── STEP 8: Create launcher ─────────────────────────────────────────────────
mkdir -p "$HOME/.local/bin"

cat > "$HOME/.local/bin/jamila" << LAUNCHEOF
#!/usr/bin/env bash
source "$VENV/bin/activate"
python3 "$INSTALL_DIR/jamila_core.py" "\$@"
LAUNCHEOF

chmod +x "$HOME/.local/bin/jamila"

# Add to PATH if needed
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
  SHELL_RC=""
  [ -f "$HOME/.bashrc" ] && SHELL_RC="$HOME/.bashrc"
  [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
  if [ -n "$SHELL_RC" ]; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo "  Added ~/.local/bin to PATH in $SHELL_RC"
  fi
fi

# Also try system-wide
if sudo ln -sf "$HOME/.local/bin/jamila" /usr/local/bin/jamila 2>/dev/null; then
  echo "  ✓ Global launcher at /usr/local/bin/jamila"
fi

# ─── DONE ────────────────────────────────────────────────────────────────────
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║  ✓ Jamila is installed!                           ║"
echo "╠════════════════════════════════════════════════════╣"
echo "║  Run:  jamila                                     ║"
echo "║  Or:   python3 ~/.jamila/jamila_core.py           ║"
echo "╠════════════════════════════════════════════════════╣"
echo "║  First run: Coqui TTS model loads (~30 seconds)  ║"
echo "║  Then: speak your commands or type them           ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""
echo "Getting started:"
echo "  Say 'help' to hear what Jamila can do"
echo "  Say 'remind me to...' to set reminders"
echo "  Ask any question naturally"
echo ""

# Optionally start immediately
read -rp "Start Jamila now? [Y/n]: " START
if [[ "${START:-Y}" =~ ^[Yy]$ ]]; then
  exec "$HOME/.local/bin/jamila"
fi
