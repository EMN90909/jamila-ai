# modules/tts.py
import pyttsx3
from config import Config

class TTS:
    def __init__(self):
        self.engine_name = Config.TTS_ENGINE
        self.engine = None
        self._init_engine()
    
    def _init_engine(self):
        """Initialize pyttsx3 (offline)"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)  # Clear speech speed
            self.engine.setProperty('volume', 0.9)  # Loud enough
            # Try to set a clear voice
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'english' in voice.name.lower() and 'female' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
        except Exception as e:
            print(f"⚠️  TTS init error: {e}")
    
    def speak(self, text, block=True):
        """Speak text aloud"""
        if not text:
            return
        if not self.engine:
            print(f"[TTS] {text}")
            return
        try:
            # Clean text for TTS (remove markdown, etc.)
            clean = text.replace('*', '').replace('#', '').strip()
            self.engine.say(clean)
            if block:
                self.engine.runAndWait()
        except Exception as e:
            print(f"[TTS Error] {e}")
    
    def speak_async(self, text):
        """Speak without blocking (for background feedback)"""
        self.speak(text, block=False)
    
    def stop(self):
        """Stop current speech"""
        if self.engine:
            self.engine.stop()
