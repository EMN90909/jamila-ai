# modules/ai_providers.py
import requests
import json
from config import Config

class AIManager:
    def __init__(self):
        self.providers = {}
        self._setup_providers()
    
    def _setup_providers(self):
        """Register configured providers"""
        if Config.DEEPSEEK_KEY and Config.DEEPSEEK_URL:
            self.providers['deepseek'] = self._call_deepseek
        if Config.OPENROUTER_KEY and Config.OPENROUTER_URL:
            self.providers['openrouter'] = self._call_openrouter
        if Config.GEMINI_KEY and Config.GEMINI_URL:
            self.providers['gemini'] = self._call_gemini
    
    def ask(self, prompt, system_prompt="You are Jamila, a helpful voice assistant for blind users. Be concise, clear, and descriptive. Avoid visual references. Use plain text."):
        """Try providers in order. Return first successful response."""
        if not Config.is_online():
            return "Offline: AI requires internet. Try offline commands like 'open firefox' or 'play music'."
        
        last_error = None
        for provider_name in Config.AI_ORDER:
            if provider_name in self.providers:
                try:
                    return self.providers[provider_name](prompt, system_prompt)
                except Exception as e:
                    last_error = e
                    continue
        
        return f"AI error: All providers failed. {str(last_error)[:100]}"
    
    def _call_deepseek(self, prompt, system_prompt):
        headers = {
            "Authorization": f"Bearer {Config.DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.3
        }
        r = requests.post(Config.DEEPSEEK_URL, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    
    def _call_openrouter(self, prompt, system_prompt):
        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://jamila.example",  # Required by OpenRouter
            "X-Title": "Jamila Core"
        }
        payload = {
            "model": "openrouter/auto",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300
        }
        r = requests.post(Config.OPENROUTER_URL, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    
    def _call_gemini(self, prompt, system_prompt):
        headers = {
            "Content-Type": "application/json"
        }
        # Gemini REST API format
        contents = [{"parts": [{"text": prompt}]}]
        payload = {"contents": contents}
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}
        
        url = f"{Config.GEMINI_URL}?key={Config.GEMINI_KEY}"
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        r.raise_for_status()
        j = r.json()
        return j['candidates'][0]['content']['parts'][0]['text'].strip()
