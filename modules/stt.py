# modules/stt.py
import queue
import sounddevice as sd
import numpy as np
from config import Config

class STT:
    def __init__(self):
        self.engine = Config.STT_ENGINE
        self.language = Config.STT_LANGUAGE
        self.running = False
        self.audio_queue = queue.Queue()
        
        if self.engine == 'vosk':
            self._init_vosk()
    
    def _init_vosk(self):
        """Initialize offline Vosk recognizer"""
        try:
            from vosk import Model, KaldiRecognizer
            if not Config.VOSK_MODEL_PATH.exists():
                raise FileNotFoundError("Vosk model not found. Run run.sh first.")
            self.model = Model(str(Config.VOSK_MODEL_PATH))
            self.recognizer = KaldiRecognizer(self.model, 16000)
        except ImportError:
            print("⚠️  Vosk not installed. Install with: pip install vosk")
            self.engine = 'fallback'
    
    def listen(self, timeout=10):
        """Listen for speech and return text. Timeout in seconds."""
        if self.engine == 'vosk':
            return self._listen_vosk(timeout)
        else:
            return self._listen_fallback(timeout)
    
    def _listen_vosk(self, timeout):
        """Offline recognition using Vosk"""
        import json
        self.running = True
        result = ""
        
        def callback(indata, frames, time_info, status):
            if self.recognizer.AcceptWaveform(indata.tobytes()):
                nonlocal result
                result = json.loads(self.recognizer.Result())['text']
            return (None, False)
        
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=8000, 
                                 dtype='int16', channels=1, callback=callback):
                import time
                start = time.time()
                while self.running and (time.time() - start) < timeout:
                    if result.strip():
                        return result.strip()
                    sd.sleep(100)
        except Exception as e:
            return f"[STT Error] {e}"
        finally:
            self.running = False
        
        # Final partial result
        final = self.recognizer.FinalResult()
        return json.loads(final).get('text', '').strip()
    
    def _listen_fallback(self, timeout):
        """Fallback: return placeholder (extend with SpeechRecognition if needed)"""
        return "[Offline mode: voice input unavailable without Vosk]"
    
    def stop(self):
        """Stop listening"""
        self.running = False
