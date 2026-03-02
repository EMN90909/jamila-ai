# modules/search.py
import requests
from duckduckgo_search import DDGS
from config import Config

class WebSearch:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Jamila/1.0; +https://jamila.example)'
        })
    
    def search(self, query, max_results=5):
        """Search DuckDuckGo without API key. Returns list of (title, url, snippet)"""
        if not Config.is_online():
            return [("Offline", "", "Internet not available. Please connect to search the web.")]
        
        try:
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    title = r.get('title', 'No title')
                    url = r.get('href', '')
                    body = r.get('body', '')
                    results.append((title, url, body[:200] + "..." if len(body) > 200 else body))
            
            if not results:
                return [(f"No results for '{query}'", "", "Try different keywords.")]
            return results
        except Exception as e:
            return [("Search error", "", f"Could not search: {str(e)[:100]}")]
    
    def open_result(self, url):
        """Open URL in default browser"""
        import webbrowser
        webbrowser.open(url)
        return f"Opened: {url}"
