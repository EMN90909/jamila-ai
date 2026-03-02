# 🌸 jamila-core — Voice Assistant for Blind Users

A lightweight, Linux-first Python assistant designed **specifically for blind and visually impaired users** to control their computer using voice commands.

## ✨ Key Features

### 🔊 Voice-First Interaction
- Press `SPACE` to toggle microphone listening
- Press `ENTER` to execute commands
- Press `ESC` to cancel / stop listening
- All feedback via clear, paced Text-to-Speech

### 📴 Offline Mode (No Internet Required)
- Open/close applications
- Create, edit, delete text files
- Play local music files
- Control system volume
- Basic window management (maximize, resize)

### 🌐 Online Mode (When Connected)
- Web search via DuckDuckGo (no API key needed)
- AI assistance via DeepSeek, OpenRouter, or Gemini
- YouTube search for music

### 🔐 Privacy & Security
- API keys stored in `.env` (never committed to Git)
- Local credentials in `credentials/` with `chmod 600`
- No telemetry, no data collection

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/jamila-core.git
cd jamila-core

# 2. Run installer (installs deps + Vosk offline model)
chmod +x run.sh
./run.sh

# 3. Configure API keys (optional, for online AI)
cp .env.example .env
nano .env  # Add your DeepSeek/OpenRouter/Gemini keys
chmod 600 .env

# 4. Run Jamila
source .venv/bin/activate
python3 jamila_core.py
