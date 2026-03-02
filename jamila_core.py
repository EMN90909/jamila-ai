#!/usr/bin/env python3
# jamila_core.py
import re
import shlex
from config import Config
from modules.tts import TTS
from modules.stt import STT
from modules.ai_providers import AIManager
from modules.actions import Actions
from modules.search import WebSearch
from modules.voice_control import VoiceControl

# Initialize core components
tts = TTS()
stt = STT()
ai = AIManager()
actions = Actions()
search = WebSearch()

def process_command(cmd: str):
    """Parse and execute voice commands"""
    cmd = cmd.lower().strip()
    if not cmd:
        return
    
    tts.speak("Processing...")
    
    # === OFFLINE COMMANDS (work without internet) ===
    
    # Open app: "open firefox", "open ~/docs"
    if cmd.startswith('open '):
        target = cmd[5:].strip()
        result = actions.open_app(target)
        tts.speak(result)
        return
    
    # Close app: "close firefox"
    if cmd.startswith('close '):
        proc = cmd[6:].strip()
        result = actions.close_app(proc)
        tts.speak(result)
        return
    
    # File operations
    if cmd.startswith('create file '):
        parts = cmd.split(' ', 3)
        if len(parts) >= 3:
            path = parts[2]
            content = parts[3] if len(parts) > 3 else ""
            result = actions.create_file(path, content)
            tts.speak(result)
        return
    
    if cmd.startswith('edit file '):
        parts = cmd.split(' ', 3)
        if len(parts) >= 4:
            path, content = parts[2], parts[3]
            result = actions.edit_file(path, content)
            tts.speak(result)
        return
    
    if cmd.startswith('delete file '):
        path = cmd[12:].strip()
        result = actions.delete_file(path)
        tts.speak(result)
        return
    
    # Music
    if cmd.startswith('play '):
        query = cmd[5:].strip()
        result = actions.play_music(query)
        tts.speak(result)
        return
    
    # Volume
    if cmd == 'volume up' or cmd == 'turn up volume':
        tts.speak(actions.volume_up())
        return
    if cmd == 'volume down' or cmd == 'turn down volume':
        tts.speak(actions.volume_down())
        return
    if cmd.startswith('set volume '):
        try:
            percent = int(''.join(filter(str.isdigit, cmd)))
            tts.speak(actions.set_volume(percent))
        except:
            tts.speak("Please say a number, like 'set volume 50'")
        return
    
    # Window
    if 'maximize' in cmd:
        tts.speak(actions.maximize_window())
        return
    if cmd.startswith('resize '):
        nums = re.findall(r'\d+', cmd)
        if len(nums) >= 2:
            tts.speak(actions.resize_window(nums[0], nums[1]))
        else:
            tts.speak("Say resize with two numbers, like 'resize 1200 800'")
        return
    
    # === ONLINE COMMANDS (require internet) ===
    
    # Web search
    if cmd.startswith('search '):
        query = cmd[7:].strip()
        tts.speak(f"Searching for {query}")
        results = search.search(query, max_results=3)
        # Speak top result
        title, url, snippet = results[0]
        tts.speak(f"Top result: {title}. {snippet}")
        # Optionally open browser
        # search.open_result(url)
        return
    
    # AI query
    if cmd.startswith('ai ') or cmd.startswith('ask '):
        query = cmd.split(' ', 1)[1].strip()
        tts.speak("Thinking...")
        response = ai.ask(query)
        tts.speak(response)
        return
    
    # Help
    if cmd in ['help', 'what can you do', 'commands']:
        help_text = (
            "Offline commands: open app, close app, create file, edit file, delete file, "
            "play music, volume up, volume down, set volume, maximize, resize. "
            "Online commands: search web, ask ai. "
            "Press space to listen, enter to execute, escape to cancel."
        )
        tts.speak(help_text)
        return
    
    # Fallback
    tts.speak("Command not recognized. Say help for available commands.")

def main():
    """Main application loop"""
    tts.speak("Jamila ready. Press space to start listening.")
    
    # Setup voice control with command handler
    voice = VoiceControl(tts, stt)
    voice.set_command_handler(process_command)
    
    # Keep alive
    try:
        voice.wait()
    except KeyboardInterrupt:
        tts.speak("Shutting down. Goodbye.")

if __name__ == '__main__':
    main()
