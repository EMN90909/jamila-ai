#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════╗
# ║  jamila_core.py — Jamila Voice-First AI for Linux           ║
# ║  Designed for blind and visually impaired users             ║
# ║  Voice input via microphone, voice output via Coqui TTS     ║
# ╚══════════════════════════════════════════════════════════════╝

import os
import sys
import json
import threading
import time
import sqlite3
import subprocess
import webbrowser
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

# ─── PATHS ────────────────────────────────────────────────────────────────────
INSTALL_DIR  = Path.home() / ".jamila"
KEY_FILE     = INSTALL_DIR / ".jamila_key"
DB_PATH      = INSTALL_DIR / "local.db"
ICON_PATH    = INSTALL_DIR / "jamila.png"
JAMILA_SERVER = "https://jamila.onrender.com"

# ─── TTS SETUP ────────────────────────────────────────────────────────────────
# We try Coqui TTS first (neural, natural), fall back to espeak then pyttsx3
_tts_engine = None
_tts_mode = None

def init_tts():
    global _tts_engine, _tts_mode
    # Try Coqui TTS
    try:
        from TTS.api import TTS as CoquiTTS
        print("→ Loading Coqui TTS neural voice model (first run may take 30s)...")
        _tts_engine = CoquiTTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False, gpu=False)
        _tts_mode = "coqui"
        print("✓ Coqui TTS ready (neural voice)")
        return
    except Exception as e:
        print(f"  Coqui TTS not available ({e}), trying espeak...")

    # Try espeak-ng (better than pyttsx3 espeak)
    try:
        result = subprocess.run(["espeak-ng", "--version"], capture_output=True, timeout=3)
        if result.returncode == 0:
            _tts_mode = "espeak"
            print("✓ espeak-ng TTS ready")
            return
    except Exception: pass

    # Fall back to pyttsx3
    try:
        import pyttsx3
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty('rate', 155)
        _tts_engine.setProperty('volume', 0.95)
        _tts_mode = "pyttsx3"
        print("✓ pyttsx3 TTS ready")
        return
    except Exception as e:
        print(f"⚠ No TTS available: {e}")
        _tts_mode = "print"

def speak(text, blocking=True):
    """Speak text aloud using the best available TTS engine."""
    if not text or not text.strip():
        return

    # Update GUI response box if available
    if _gui_window:
        _gui_window.set_response(text)

    clean = text.strip()
    print(f"\n🔊 Jamila: {clean}\n")

    if _tts_mode == "coqui" and _tts_engine:
        try:
            import tempfile, soundfile as sf, sounddevice as sd
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp = f.name
            _tts_engine.tts_to_file(text=clean, file_path=tmp)
            data, samplerate = sf.read(tmp)
            sd.play(data, samplerate)
            if blocking: sd.wait()
            os.unlink(tmp)
            return
        except Exception as e:
            print(f"  Coqui speak error: {e}")

    if _tts_mode == "espeak":
        try:
            cmd = ["espeak-ng", "-s", "145", "-p", "50", "-v", "en", clean]
            if blocking:
                subprocess.run(cmd, capture_output=True)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception as e:
            print(f"  espeak error: {e}")

    if _tts_mode == "pyttsx3" and _tts_engine:
        try:
            _tts_engine.say(clean)
            _tts_engine.runAndWait()
            return
        except Exception: pass

# ─── SPEECH RECOGNITION ───────────────────────────────────────────────────────
_recognizer = None
_microphone = None
_listening = False

def init_stt():
    global _recognizer, _microphone
    try:
        import speech_recognition as sr
        _recognizer = sr.Recognizer()
        _recognizer.dynamic_energy_threshold = True
        _recognizer.pause_threshold = 0.8
        _microphone = sr.Microphone()
        # Calibrate for ambient noise
        with _microphone as source:
            _recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✓ Microphone ready")
        return True
    except Exception as e:
        print(f"⚠ Microphone not available: {e}")
        return False

def listen_once(timeout=8):
    """Listen for one spoken command. Returns text or None."""
    global _listening
    if not _recognizer or not _microphone:
        return None
    import speech_recognition as sr
    _listening = True
    if _gui_window: _gui_window.set_listening(True)
    try:
        with _microphone as source:
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        text = _recognizer.recognize_google(audio)
        return text.strip()
    except sr.WaitTimeoutError:
        return None
    except sr.UnknownValueError:
        return None
    except Exception as e:
        print(f"STT error: {e}")
        return None
    finally:
        _listening = False
        if _gui_window: _gui_window.set_listening(False)

# ─── GUI WINDOW ───────────────────────────────────────────────────────────────
_gui_window = None

class JamilaWindow:
    """GTK main window — accessible, voice-centric UI with Jamila icon and response box."""

    def __init__(self):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GLib, GdkPixbuf, Pango, Gdk
        self.Gtk = Gtk
        self.GLib = GLib
        self.Pango = Pango

        self.window = Gtk.Window()
        self.window.set_title("Jamila — Voice AI")
        self.window.set_default_size(520, 620)
        self.window.set_border_width(0)
        self.window.connect("destroy", Gtk.main_quit)
        self.window.set_resizable(True)

        # Dark background via CSS
        css = b"""
        window { background-color: #0a0a08; }
        .header-box { background-color: #111108; border-bottom: 1px solid #2a2a1e; }
        .response-area { background-color: #0f0f0a; border: 1px solid #2a2a1e; border-radius: 12px; padding: 16px; }
        .status-label { font-size: 13px; }
        .mic-button {
            background: #c8973a;
            border-radius: 50px;
            border: none;
            color: #0a0a08;
            font-size: 22px;
            font-weight: bold;
            padding: 20px 40px;
            transition: all 0.2s;
        }
        .mic-button:hover { background: #e8b84b; }
        .mic-button.listening { background: #e74c3c; }
        .type-button { background: #1e1e18; border: 1px solid #3a3a2e; border-radius: 8px; color: #c8c8a0; padding: 10px 20px; }
        .type-button:hover { background: #2a2a20; }
        .cmd-entry {
            background-color: #1a1a12;
            border: 1px solid #3a3a2e;
            border-radius: 8px;
            color: #f5f0e8;
            font-family: monospace;
            font-size: 14px;
            padding: 10px 14px;
        }
        .response-label { font-size: 16px; line-height: 1.6; color: #f5f0e8; }
        .response-title { font-size: 12px; font-weight: bold; letter-spacing: 2px; color: #c8973a; }
        .history-label { font-size: 13px; color: #888870; }
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.window.add(main_box)

        # ── HEADER ──
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header.get_style_context().add_class('header-box')
        header.set_border_width(20)
        main_box.pack_start(header, False, False, 0)

        # Logo + icon row
        logo_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.pack_start(logo_row, False, False, 0)

        # Try to load jamila.png icon
        try:
            icon_buf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(ICON_PATH), 52, 52, True)
            icon_img = Gtk.Image.new_from_pixbuf(icon_buf)
            logo_row.pack_start(icon_img, False, False, 0)
        except Exception:
            # Fallback emoji icon
            icon_lbl = Gtk.Label("🎙")
            icon_lbl.set_markup('<span font="32">🎙</span>')
            logo_row.pack_start(icon_lbl, False, False, 0)

        name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        logo_row.pack_start(name_box, False, False, 0)

        title_lbl = Gtk.Label()
        title_lbl.set_markup('<span font="Fraunces, serif" size="20000" weight="heavy" foreground="#f5f0e8">Ja<i><span foreground="#c8973a">mila</span></i></span>')
        title_lbl.set_xalign(0)
        name_box.pack_start(title_lbl, False, False, 0)

        tagline_lbl = Gtk.Label()
        tagline_lbl.set_markup('<span size="10000" foreground="#888870">Voice-First AI · Listening for you</span>')
        tagline_lbl.set_xalign(0)
        name_box.pack_start(tagline_lbl, False, False, 0)

        # Status label (top right)
        self.status_label = Gtk.Label("Ready")
        self.status_label.get_style_context().add_class('status-label')
        self.status_label.set_markup('<span foreground="#27ae60" size="10000">● Ready</span>')
        logo_row.pack_end(self.status_label, False, False, 0)

        # Plan/calls label
        self.calls_label = Gtk.Label()
        self.calls_label.set_markup('<span foreground="#888870" size="9000">Checking plan...</span>')
        self.calls_label.set_xalign(0)
        header.pack_start(self.calls_label, False, False, 0)

        # ── RESPONSE AREA ──
        resp_wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        resp_wrapper.set_border_width(16)
        main_box.pack_start(resp_wrapper, True, True, 0)

        resp_title = Gtk.Label()
        resp_title.set_markup('<span foreground="#c8973a" size="9000" weight="bold" letter_spacing="2000">JAMILA\'S RESPONSE</span>')
        resp_title.set_xalign(0)
        resp_wrapper.pack_start(resp_title, False, False, 0)

        # Scrollable response box
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        resp_wrapper.pack_start(scrolled, True, True, 0)

        resp_viewport = Gtk.Viewport()
        resp_viewport.get_style_context().add_class('response-area')
        scrolled.add(resp_viewport)

        self.response_label = Gtk.Label()
        self.response_label.set_markup('<span foreground="#555540" size="14000" style="italic">Waiting for your command...\n\nPress the microphone button or type a command below.</span>')
        self.response_label.set_line_wrap(True)
        self.response_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.response_label.set_xalign(0)
        self.response_label.set_yalign(0)
        self.response_label.set_selectable(True)  # Screen readers can select text
        self.response_label.set_margin_start(4)
        self.response_label.set_margin_top(4)
        self.response_label.get_style_context().add_class('response-label')
        resp_viewport.add(self.response_label)

        # History area
        hist_title = Gtk.Label()
        hist_title.set_markup('<span foreground="#c8973a" size="9000" weight="bold" letter_spacing="2000">CONVERSATION</span>')
        hist_title.set_xalign(0)
        resp_wrapper.pack_start(hist_title, False, False, 0)

        history_scroll = Gtk.ScrolledWindow()
        history_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        history_scroll.set_size_request(-1, 120)
        resp_wrapper.pack_start(history_scroll, False, False, 0)

        self.history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        history_scroll.add(self.history_box)

        # ── CONTROLS ──
        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        controls.set_border_width(16)
        main_box.pack_start(controls, False, False, 0)

        # Mic button (BIG - accessible for blind users)
        self.mic_btn = Gtk.Button()
        self.mic_btn.get_style_context().add_class('mic-button')
        self.mic_label = Gtk.Label()
        self.mic_label.set_markup('<span size="18000" weight="bold">🎙  Press to Speak</span>')
        self.mic_btn.add(self.mic_label)
        self.mic_btn.connect("clicked", self.on_mic_click)
        self.mic_btn.set_tooltip_text("Click to speak a command (or press Space)")
        controls.pack_start(self.mic_btn, False, False, 0)

        # Keyboard shortcut: Space = mic
        self.window.connect("key-press-event", self.on_key_press)
        self.mic_btn.set_can_focus(True)

        # Divider
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        controls.pack_start(sep, False, False, 0)

        # Type command row
        type_label = Gtk.Label()
        type_label.set_markup('<span foreground="#888870" size="10000">Or type a command:</span>')
        type_label.set_xalign(0)
        controls.pack_start(type_label, False, False, 0)

        cmd_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        controls.pack_start(cmd_row, False, False, 0)

        self.cmd_entry = Gtk.Entry()
        self.cmd_entry.get_style_context().add_class('cmd-entry')
        self.cmd_entry.set_placeholder_text("Type a command or question and press Enter...")
        self.cmd_entry.connect("activate", self.on_cmd_enter)
        cmd_row.pack_start(self.cmd_entry, True, True, 0)

        send_btn = Gtk.Button()
        send_btn.get_style_context().add_class('type-button')
        send_btn.add(Gtk.Label("Send →"))
        send_btn.connect("clicked", self.on_cmd_enter)
        cmd_row.pack_start(send_btn, False, False, 0)

        # Quick commands
        quick_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls.pack_start(quick_row, False, False, 0)
        for label, cmd in [("Help", "help"), ("Reminders", "reminders"), ("Notes", "notes"), ("Status", "key status")]:
            btn = Gtk.Button(label=label)
            btn.get_style_context().add_class('type-button')
            btn.connect("clicked", lambda b, c=cmd: self.run_cmd(c))
            quick_row.pack_start(btn, True, True, 0)

        self.window.show_all()

    def set_status(self, text, color="#c8973a"):
        self.GLib.idle_add(lambda: self.status_label.set_markup(f'<span foreground="{color}" size="10000">● {text}</span>') or False)

    def set_listening(self, on):
        if on:
            self.GLib.idle_add(lambda: self.mic_label.set_markup('<span size="18000" weight="bold">🔴  Listening...</span>') or False)
            self.GLib.idle_add(lambda: self.mic_btn.get_style_context().add_class('listening') or False)
            self.set_status("Listening...", "#e74c3c")
        else:
            self.GLib.idle_add(lambda: self.mic_label.set_markup('<span size="18000" weight="bold">🎙  Press to Speak</span>') or False)
            self.GLib.idle_add(lambda: self.mic_btn.get_style_context().remove_class('listening') or False)
            self.set_status("Ready", "#27ae60")

    def set_response(self, text):
        def _update():
            escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            self.response_label.set_markup(f'<span foreground="#f5f0e8" size="15000">{escaped}</span>')
            return False
        self.GLib.idle_add(_update)

    def set_thinking(self):
        self.set_response("Thinking...")
        self.set_status("Thinking...", "#c8973a")

    def add_history(self, role, text):
        def _update():
            color = "#c8973a" if role == "you" else "#888870"
            prefix = "You:" if role == "you" else "Jamila:"
            lbl = self.Gtk.Label()
            short = text[:120] + ("..." if len(text) > 120 else "")
            escaped = short.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            lbl.set_markup(f'<span foreground="{color}" size="10000" weight="bold">{prefix}</span> <span foreground="#aaa890" size="10000">{escaped}</span>')
            lbl.set_xalign(0)
            lbl.set_line_wrap(True)
            self.history_box.pack_start(lbl, False, False, 0)
            self.history_box.show_all()
            return False
        self.GLib.idle_add(_update)

    def set_calls_info(self, today, daily_lim, month, monthly_lim, plan):
        def _update():
            self.calls_label.set_markup(
                f'<span foreground="#888870" size="9000">'
                f'Plan: <span foreground="#c8973a">{plan.upper()}</span> · '
                f'Today: {today}/{daily_lim} calls · '
                f'Month: {month}/{monthly_lim} calls'
                f'</span>'
            )
            return False
        self.GLib.idle_add(_update)

    def on_mic_click(self, btn):
        threading.Thread(target=self._do_listen, daemon=True).start()

    def on_key_press(self, widget, event):
        import gi; from gi.repository import Gdk
        if event.keyval == Gdk.KEY_space and not self.cmd_entry.has_focus():
            self.on_mic_click(None)
            return True
        return False

    def on_cmd_enter(self, widget):
        cmd = self.cmd_entry.get_text().strip()
        if cmd:
            self.cmd_entry.set_text("")
            threading.Thread(target=self.run_cmd, args=(cmd,), daemon=True).start()

    def _do_listen(self):
        speak("Listening", blocking=False)
        text = listen_once()
        if text:
            self.add_history("you", text)
            self.run_cmd(text)
        else:
            speak("I didn't hear anything. Please try again.")

    def run_cmd(self, cmd):
        result = parse_and_run(cmd)
        if result == 'exit':
            self.GLib.idle_add(self.Gtk.main_quit)

def run_gui():
    global _gui_window
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        _gui_window = JamilaWindow()
        _gui_window.set_status("Loading...", "#c8973a")
        # Load status in background
        threading.Thread(target=_update_call_status, daemon=True).start()
        import gi.repository.Gtk as Gtk
        Gtk.main()
        return True
    except Exception as e:
        print(f"GUI not available ({e}), falling back to terminal mode")
        return False

def _update_call_status():
    """Background: fetch call status from server and update GUI."""
    try:
        key = load_key()
        if not key or not _gui_window: return
        r = requests.post(f"{JAMILA_SERVER}/api/verify-key", json={"key": key}, timeout=8)
        d = r.json()
        if d.get("valid"):
            _gui_window.set_calls_info(
                d.get('calls_today', 0), d.get('daily_limit', 10),
                d.get('calls_month', 0), d.get('monthly_limit', 300),
                d.get('plan', 'free')
            )
            _gui_window.set_status("Connected", "#27ae60")
        else:
            _gui_window.set_status("Key Invalid", "#e74c3c")
    except Exception as e:
        if _gui_window: _gui_window.set_status("Offline", "#888870")

# ─── KEY MANAGEMENT ───────────────────────────────────────────────────────────
def load_key():
    return KEY_FILE.read_text().strip() if KEY_FILE.exists() else None

def save_key(key):
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(key.strip())
    KEY_FILE.chmod(0o600)

def verify_key(key):
    try:
        r = requests.post(f"{JAMILA_SERVER}/api/verify-key", json={"key": key}, timeout=10)
        return r.json()
    except Exception as e:
        return {"valid": False, "reason": f"Cannot reach server: {e}"}

def prompt_for_key_spoken():
    """Ask user for activation key — spoken instructions, typed input."""
    speak("Welcome to Jamila. I need your activation key to get started. You can get your key by visiting jamila dot onrender dot com and signing in to your dashboard.", blocking=True)
    print("\n╔══════════════════════════════════════╗")
    print("║  Jamila needs your activation key   ║")
    print("║  Get it at: jamila.onrender.com     ║")
    print("╚══════════════════════════════════════╝\n")
    key = input("Enter activation key (JML-XXXX-...): ").strip()
    if not key:
        speak("No key entered. Goodbye.")
        sys.exit(1)
    speak("Verifying your key, please wait.", blocking=True)
    result = verify_key(key)
    if not result.get("valid"):
        msg = result.get("reason", "Invalid key")
        speak(f"Sorry, your key was rejected. {msg}. Please visit jamila dot onrender dot com to check your account.")
        print(f"\n❌ {msg}")
        sys.exit(1)
    plan = result.get("plan", "free")
    speak(f"Key verified! Welcome to Jamila. Your plan is {plan}. You can now use voice commands.", blocking=True)
    print(f"✓ Key verified. Plan: {plan}")
    save_key(key)
    return key, result

# ─── LOCAL DATABASE ───────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        remind_at TEXT NOT NULL,
        done INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        content TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    conn.commit()
    conn.close()

def db_exec(sql, params=()):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    rows = c.fetchall()
    conn.close()
    return rows

# ─── AI VIA JAMILA SERVER ─────────────────────────────────────────────────────
_conv_history = []

def ask_ai(prompt):
    key = load_key()
    if not key:
        return "No activation key found. Please run setup."
    if _gui_window:
        _gui_window.set_thinking()
    payload = {
        "key": key,
        "prompt": prompt,
        "history": _conv_history[-8:]  # last 4 turns
    }
    try:
        r = requests.post(f"{JAMILA_SERVER}/api/ai/chat", json=payload, timeout=30)
        data = r.json()
        if r.status_code == 403:
            return data.get("error", "Access denied. Check your subscription.")
        if r.status_code == 429:
            return data.get("error", "Daily or monthly AI call limit reached. Please renew or upgrade.")
        if r.status_code != 200:
            return f"Server error: {data.get('error', 'Unknown error')}"
        response = data.get("response", "")
        _conv_history.append({"role": "user", "content": prompt})
        _conv_history.append({"role": "assistant", "content": response})
        db_exec("INSERT INTO history (role, content) VALUES (?,?)", ("user", prompt))
        db_exec("INSERT INTO history (role, content) VALUES (?,?)", ("assistant", response))
        if _gui_window: _gui_window.add_history("ai", response)
        # Refresh call status after each AI call
        threading.Thread(target=_update_call_status, daemon=True).start()
        return response
    except requests.exceptions.ConnectionError:
        return "Cannot reach Jamila server. Please check your internet connection. Local commands still work."
    except Exception as e:
        return f"Error: {e}"

# ─── REMINDERS ────────────────────────────────────────────────────────────────
def parse_time(text):
    text_l = text.lower()
    now = datetime.now()
    if "tomorrow" in text_l:
        b = now + timedelta(days=1)
        if "morning" in text_l: return b.replace(hour=8, minute=0)
        if "noon" in text_l: return b.replace(hour=12, minute=0)
        if "evening" in text_l: return b.replace(hour=18, minute=0)
        if "night" in text_l: return b.replace(hour=20, minute=0)
        return b.replace(hour=9, minute=0)
    if "tonight" in text_l: return now.replace(hour=20, minute=0)
    if "today" in text_l:
        if "noon" in text_l: return now.replace(hour=12, minute=0)
        if "evening" in text_l: return now.replace(hour=18, minute=0)
        return now.replace(hour=17, minute=0)
    m = re.search(r'in (\d+) (minute|hour|day)', text_l)
    if m:
        n, u = int(m.group(1)), m.group(2)
        if "minute" in u: return now + timedelta(minutes=n)
        if "hour" in u: return now + timedelta(hours=n)
        if "day" in u: return now + timedelta(days=n)
    # look for "at HH:MM" or "at X pm/am"
    m2 = re.search(r'at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_l)
    if m2:
        hr = int(m2.group(1)); mn = int(m2.group(2) or 0)
        ap = m2.group(3)
        if ap == 'pm' and hr < 12: hr += 12
        if ap == 'am' and hr == 12: hr = 0
        t = now.replace(hour=hr, minute=mn, second=0)
        if t < now: t += timedelta(days=1)
        return t
    return now + timedelta(hours=1)

def add_reminder(text):
    remind_at = parse_time(text)
    clean = re.sub(r'remind me to |remind me |tomorrow|tonight|today|at \d+.*?(?:am|pm)?|in \d+ (?:minutes?|hours?|days?)', '', text, flags=re.IGNORECASE).strip()
    if not clean: clean = text
    db_exec("INSERT INTO reminders (text, remind_at) VALUES (?,?)", (clean, remind_at.isoformat()))
    time_str = remind_at.strftime("%B %d at %I:%M %p")
    return f"Reminder set. I will remind you to {clean} on {time_str}."

def list_reminders():
    rows = db_exec("SELECT text, remind_at FROM reminders WHERE done=0 ORDER BY remind_at LIMIT 10")
    if not rows: return "You have no upcoming reminders."
    parts = [f"{t} at {dt[:16].replace('T', ' ')}" for t, dt in rows]
    return "Your upcoming reminders are: " + ". ".join(parts)

def check_reminders_loop():
    while True:
        try:
            now = datetime.now().isoformat()
            due = db_exec("SELECT id, text FROM reminders WHERE remind_at <= ? AND done=0", (now,))
            for rid, text in due:
                msg = f"Reminder: {text}"
                speak(msg, blocking=False)
                if _gui_window: _gui_window.set_response("⏰ " + msg)
                db_exec("UPDATE reminders SET done=1 WHERE id=?", (rid,))
        except Exception: pass
        time.sleep(30)

# ─── NOTES ────────────────────────────────────────────────────────────────────
def save_note(text):
    title = text[:40]
    db_exec("INSERT INTO notes (title, content) VALUES (?,?)", (title, text))
    return f"Note saved: {title}"

def list_notes():
    rows = db_exec("SELECT title, created_at FROM notes ORDER BY id DESC LIMIT 5")
    if not rows: return "You have no saved notes."
    parts = [f"{t} saved on {c[:10]}" for t, c in rows]
    return "Your recent notes: " + ". ".join(parts)

# ─── SYSTEM ACTIONS ───────────────────────────────────────────────────────────
def open_app(target):
    APPS = {
        'browser': ['firefox'], 'firefox': ['firefox'],
        'chrome': ['google-chrome'], 'terminal': ['gnome-terminal'],
        'files': ['xdg-open', str(Path.home())],
        'calculator': ['gnome-calculator'], 'settings': ['gnome-control-center'],
        'text editor': ['gedit'], 'editor': ['gedit']
    }
    key = target.lower().strip()
    cmd = APPS.get(key)
    if not cmd:
        if os.path.exists(target): cmd = ['xdg-open', target]
        else: cmd = [target]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return f"Opening {target}"
    except Exception as e:
        return f"Could not open {target}: {e}"

def close_app(name):
    try: subprocess.run(['pkill', '-f', name]); return f"Closed {name}"
    except Exception as e: return f"Error closing {name}: {e}"

def play_music(q):
    if os.path.exists(q):
        try: subprocess.Popen(['mpv', q], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return f"Now playing {q}"
        except: pass
    webbrowser.open(f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}")
    return f"Searching YouTube for {q}"

def set_volume(pct):
    try:
        p = max(0, min(100, int(pct)))
        subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{p}%'], capture_output=True)
        return f"Volume set to {p} percent"
    except Exception as e: return f"Volume error: {e}"

def adjust_window(action, w=None, h=None):
    try:
        if action == 'maximize':
            subprocess.run(['xdotool', 'getactivewindow', 'windowmaximize'])
            return "Window maximized"
        if action == 'resize' and w and h:
            subprocess.run(['xdotool', 'getactivewindow', 'windowsize', str(w), str(h)])
            return f"Window resized to {w} by {h}"
    except Exception as e: return f"Window error: {e}"

def search_web(query):
    try:
        from modules.search_ui import SearchBox
        SearchBox(query)
    except Exception:
        webbrowser.open(f"https://duckduckgo.com/?q={query.replace(' ', '+')}")
    return f"Search results opened for {query}"

def send_email_cmd(parts_str):
    return "Email sending: please say 'send email to address, subject, body' — this feature requires SMTP setup in your profile."

# ─── COMMAND PARSER ───────────────────────────────────────────────────────────
def parse_and_run(cmd):
    if not cmd or not cmd.strip():
        return
    c = cmd.strip()
    cl = c.lower()
    if _gui_window: _gui_window.add_history("you", c)

    # EXIT
    if cl in ('exit', 'quit', 'goodbye', 'bye', 'stop jamila'):
        speak("Goodbye! Have a great day.")
        return 'exit'

    # KEY SETUP
    if cl in ('setup', 'rekey', 'enter key', 'change key'):
        key, info = prompt_for_key_spoken()
        return

    # KEY STATUS
    if 'key status' in cl or 'my plan' in cl or 'how many calls' in cl:
        key = load_key()
        if not key:
            speak("No activation key. Please run setup.")
            return
        result = verify_key(key)
        if result.get('valid'):
            plan = result.get('plan', 'free')
            daily = result.get('daily_limit', 10)
            monthly = result.get('monthly_limit', 300)
            today = result.get('calls_today', 0)
            month_calls = result.get('calls_month', 0)
            msg = f"Your plan is {plan}. You have used {today} of {daily} daily AI calls, and {month_calls} of {monthly} monthly calls."
            speak(msg)
        else:
            speak(f"Your key is not valid. {result.get('reason', '')}")
        return

    # REMINDERS
    if cl.startswith('remind') or 'remind me' in cl:
        speak(add_reminder(c)); return
    if cl in ('reminders', 'list reminders', 'show reminders', 'my reminders', 'upcoming reminders'):
        speak(list_reminders()); return

    # NOTES
    if cl.startswith('note ') or cl.startswith('save note ') or cl.startswith('write note '):
        text = re.sub(r'^(note|save note|write note)\s+', '', c, flags=re.IGNORECASE)
        speak(save_note(text)); return
    if cl in ('notes', 'list notes', 'my notes', 'show notes'):
        speak(list_notes()); return

    # SYSTEM
    if cl.startswith('open '):
        speak(open_app(c[5:])); return
    if cl.startswith('close ') or cl.startswith('quit '):
        speak(close_app(re.sub(r'^(close|quit)\s+', '', cl))); return
    if cl.startswith('play ') or cl.startswith('play music'):
        speak(play_music(re.sub(r'^play\s*(music)?\s*', '', c))); return
    if cl.startswith('volume ') or 'set volume' in cl:
        num = re.search(r'(\d+)', c)
        if num: speak(set_volume(num.group(1)))
        else: speak("Please say a volume level, like 'volume 50'")
        return
    if cl.startswith('resize '):
        parts = c.split(); speak(adjust_window('resize', parts[1] if len(parts)>1 else None, parts[2] if len(parts)>2 else None)); return
    if 'maximize' in cl or 'maximise' in cl:
        speak(adjust_window('maximize')); return
    if cl.startswith('search ') or cl.startswith('search for '):
        q = re.sub(r'^search (for\s+)?', '', cl)
        speak(search_web(q)); return

    # HISTORY
    if 'clear history' in cl or 'clear conversation' in cl:
        _conv_history.clear()
        db_exec("DELETE FROM history")
        speak("Conversation history cleared."); return

    # HELP
    if cl in ('help', 'what can you do', 'commands', 'what do you do'):
        help_text = (
            "Here are things you can say to me. "
            "For AI questions: just say your question naturally, or start with 'ask'. "
            "For reminders: say 'remind me to take my medicine tomorrow morning'. "
            "For notes: say 'note, I need to call the bank'. "
            "For apps: say 'open Firefox' or 'open terminal'. "
            "For music: say 'play jazz music'. "
            "For volume: say 'volume 50'. "
            "For web search: say 'search for Python tutorials'. "
            "To hear your reminders: say 'reminders'. "
            "To check your plan: say 'my plan'. "
            "To quit: say 'goodbye'."
        )
        speak(help_text); return

    # EXPLICIT AI PREFIX
    if cl.startswith('ai ') or cl.startswith('ask ') or cl.startswith('tell me ') or cl.startswith('what is ') or cl.startswith('who is ') or cl.startswith('how do') or cl.startswith('explain ') or cl.startswith('can you '):
        q = re.sub(r'^(ai|ask|tell me)\s+', '', c, flags=re.IGNORECASE)
        response = ask_ai(q)
        speak(response)
        return

    # FALLBACK — treat as AI
    response = ask_ai(c)
    speak(response)

# ─── TERMINAL FALLBACK MODE ───────────────────────────────────────────────────
def run_terminal():
    speak("Jamila ready in terminal mode. You can type commands or questions. Type 'help' to learn what I can do.")
    print("────────────────────────────────────────────")
    print("Jamila › Terminal Mode")
    print("────────────────────────────────────────────")
    while True:
        try:
            cmd = input("jamila› ").strip()
            if parse_and_run(cmd) == 'exit':
                break
        except (KeyboardInterrupt, EOFError):
            speak("Goodbye!")
            break

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    init_db()

    # Initialize TTS early so we can speak during setup
    init_tts()

    # Check / get key
    key = load_key()
    if not key:
        key, info = prompt_for_key_spoken()
    else:
        result = verify_key(key)
        if not result.get("valid"):
            print(f"\n⚠ Key invalid: {result.get('reason')}")
            speak(f"Warning: your activation key is no longer valid. {result.get('reason', '')}. AI features are paused. Visit jamila dot onrender dot com to renew.")

    # Initialize STT
    has_mic = init_stt()

    # Start reminder checker thread
    threading.Thread(target=check_reminders_loop, daemon=True).start()

    # Try GUI first
    gui_ok = run_gui()
    if not gui_ok:
        # Fall back to terminal
        run_terminal()

if __name__ == '__main__':
    main()
