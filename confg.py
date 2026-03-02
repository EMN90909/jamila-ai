# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent / '.env')

class Config:
    # AI Providers
    DEEPSEEK_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
    
    OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_URL = os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1/chat/completions')
    
    GEMINI_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_URL = os.getenv('GEMINI_API_URL', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent')
    
    AI_ORDER = [x.strip() for x in os.getenv('AI_PROVIDER_ORDER', 'openrouter,deepseek,gemini').split(',') if x.strip()]
    
    # TTS/STT
    TTS_ENGINE = os.getenv('TTS_ENGINE', 'pyttsx3')
    STT_ENGINE = os.getenv('STT_ENGINE', 'vosk')
    STT_LANGUAGE = os.getenv('STT_LANGUAGE', 'en-us')
    
    # Audio
    MIC_INDEX = os.getenv('MIC_INDEX', 'default')
    VOLUME_STEP = int(os.getenv('VOLUME_STEP', '10'))
    
    # Paths
    PROJECT_ROOT = Path(__file__).parent
    VOSK_MODEL_PATH = PROJECT_ROOT / 'models' / 'vosk-model-small-en-us-0.15'
    CREDENTIALS_DIR = PROJECT_ROOT / 'credentials'
    
    @classmethod
    def is_online(cls):
        """Check internet connectivity"""
        import socket
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            return True
        except:
            return False
