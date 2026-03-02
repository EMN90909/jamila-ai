# modules/actions.py
import os
import subprocess
import json
from pathlib import Path
from config import Config

class Actions:
    @staticmethod
    def open_app(name):
        """Open application by name or path"""
        name = name.strip().lower()
        # Map common names
        mapping = {
            'browser': 'firefox',
            'firefox': 'firefox',
            'terminal': 'gnome-terminal',
            'files': 'nautilus',
            'music': 'rhythmbox'
        }
        cmd = mapping.get(name, name)
        
        try:
            subprocess.Popen(['xdg-open', cmd] if os.path.exists(cmd) else [cmd], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opened {name}"
        except Exception as e:
            return f"Could not open {name}: {str(e)[:50]}"
    
    @staticmethod
    def close_app(name):
        """Close application by process name"""
        try:
            subprocess.run(['pkill', '-f', name], check=False, capture_output=True)
            return f"Closed {name}"
        except Exception as e:
            return f"Close error: {str(e)[:50]}"
    
    @staticmethod
    def create_file(path, content=""):
        """Create a new text file"""
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding='utf-8')
            return f"Created file: {p.name}"
        except Exception as e:
            return f"Create error: {str(e)[:50]}"
    
    @staticmethod
    def edit_file(path, content):
        """Overwrite file content"""
        try:
            Path(path).expanduser().write_text(content, encoding='utf-8')
            return f"Updated: {Path(path).name}"
        except Exception as e:
            return f"Edit error: {str(e)[:50]}"
    
    @staticmethod
    def delete_file(path):
        """Delete a file"""
        try:
            Path(path).expanduser().unlink()
            return f"Deleted: {Path(path).name}"
        except Exception as e:
            return f"Delete error: {str(e)[:50]}"
    
    @staticmethod
    def play_music(path_or_query):
        """Play local file or search YouTube"""
        path = Path(path_or_query).expanduser()
        if path.exists():
            try:
                subprocess.Popen(['mpv', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Playing: {path.name}"
            except Exception as e:
                return f"Play error: {str(e)[:50]}"
        else:
            # Open YouTube search in browser
            import webbrowser
            query = path_or_query.replace(' ', '+')
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"Opened YouTube search for: {path_or_query}"
    
    @staticmethod
    def volume_up():
        """Increase volume by configured step"""
        step = Config.VOLUME_STEP
        try:
            subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'+{step}%'], check=False)
            return f"Volume up {step}%"
        except:
            return "Volume control unavailable"
    
    @staticmethod
    def volume_down():
        """Decrease volume"""
        step = Config.VOLUME_STEP
        try:
            subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'-{step}%'], check=False)
            return f"Volume down {step}%"
        except:
            return "Volume control unavailable"
    
    @staticmethod
    def set_volume(percent):
        """Set exact volume (0-100)"""
        try:
            p = max(0, min(100, int(percent)))
            subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', f'{p}%'], check=False)
            return f"Volume set to {p}%"
        except:
            return "Volume control unavailable"
    
    @staticmethod
    def maximize_window():
        """Maximize active window"""
        try:
            subprocess.run(['xdotool', 'getactivewindow', 'windowmaximize'], check=False)
            return "Window maximized"
        except:
            return "Window control unavailable"
    
    @staticmethod
    def resize_window(width, height):
        """Resize active window"""
        try:
            subprocess.run(['xdotool', 'getactivewindow', 'windowsize', str(width), str(height)], check=False)
            return f"Resized to {width}x{height}"
        except:
            return "Window resize unavailable"
