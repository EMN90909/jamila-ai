# modules/voice_control.py
import threading
import time
from pynput import keyboard
from modules.stt import STT
from modules.tts import TTS

class VoiceControl:
    def __init__(self, tts: TTS, stt: STT):
        self.tts = tts
        self.stt = stt
        self.listening = False
        self.running = True
        self.command_callback = None
        
        # Setup global key listener
        self.listener = keyboard.GlobalHotKeys({
            '<space>': self._toggle_listen,
            '<enter>': self._execute,
            '<esc>': self._cancel,
            '<ctrl>+<c>': self._quit
        })
        self.listener.start()
    
    def set_command_handler(self, callback):
        """Set function to handle recognized commands"""
        self.command_callback = callback
    
    def _toggle_listen(self):
        """SPACE: Toggle microphone"""
        self.listening = not self.listening
        if self.listening:
            self.tts.speak_async("Listening...")
            # Start listening thread
            threading.Thread(target=self._listen_loop, daemon=True).start()
        else:
            self.stt.stop()
            self.tts.speak_async("Stopped listening")
    
    def _listen_loop(self):
        """Continuously listen while active"""
        while self.listening and self.running:
            text = self.stt.listen(timeout=8)
            if text and text.strip():
                self.tts.speak_async(f"Heard: {text}")
                if self.command_callback:
                    # Run command handler in background
                    threading.Thread(
                        target=lambda: self.command_callback(text.strip()), 
                        daemon=True
                    ).start()
                # Auto-stop after command (optional: keep listening)
                self.listening = False
            time.sleep(0.1)
    
    def _execute(self):
        """ENTER: Execute pending command (if any)"""
        self.tts.speak("Executing...")
        # Could implement command queue here
    
    def _cancel(self):
        """ESC: Cancel current operation"""
        self.listening = False
        self.stt.stop()
        self.tts.speak("Cancelled")
    
    def _quit(self):
        """CTRL+C: Graceful shutdown"""
        self.running = False
        self.listening = False
        self.stt.stop()
        self.tts.speak("Goodbye")
        time.sleep(0.5)
        import sys
        sys.exit(0)
    
    def wait(self):
        """Keep main thread alive"""
        while self.running:
            time.sleep(1)
