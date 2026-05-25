import logging
import time
import threading
import ctypes
from typing import Callable, Optional, Dict, Any

logger = logging.getLogger("ScreenMonitor")

class ScreenMonitor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScreenMonitor, cls).__new__(cls)
            cls._instance._init_monitor()
        return cls._instance

    def _init_monitor(self):
        self.interval = 10
        self.on_context_change: Optional[Callable[[Dict[str, Any]], None]] = None
        self.last_app = ""
        self.running = False
        self._thread: Optional[threading.Thread] = None

        self.CODING_APPS = ["visual studio", "vscode", "pycharm", "code", "notepad++", "sublime", "terminal", "powershell", "cmd.exe"]
        self.GAMING_APPS = ["steam", "valorant", "minecraft", "epic games", "battle.net", "league of legends", "csgo"]
        self.BROWSING_APPS = ["chrome", "firefox", "edge", "opera", "safari"]
        self.MEDIA_APPS = ["spotify", "vlc", "netflix", "youtube"]

    def start(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        if self.running:
            return
        if callback:
            self.on_context_change = callback
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, name="ScreenMonitor-Thread", daemon=True)
        self._thread.start()
        logger.info("Screen Monitor system started.")

    def stop(self):
        self.running = False

    def get_active_app(self) -> str:
        try:
            # Windows API to get active window title
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value or ""
        except Exception as e:
            logger.error(f"Failed to get active window title: {e}")
            return ""

    def analyze_context(self) -> Dict[str, Any]:
        app_title = self.get_active_app()
        app_title_lower = app_title.lower()
        
        context_type = "other"
        suggestion = ""
        
        if any(app in app_title_lower for app in self.CODING_APPS):
            context_type = "coding"
            suggestion = "Visual Studio / Editor açık görünüyor. Kod geliştirmeye veya debug etmeye devam edelim mi?"
        elif any(app in app_title_lower for app in self.GAMING_APPS):
            context_type = "gaming"
            suggestion = "Oyun moduna geçildi. Performansı artırmak için arka plan işlemlerini optimize edebilirim."
        elif any(app in app_title_lower for app in self.BROWSING_APPS):
            context_type = "browsing"
            suggestion = "Tarayıcı açık. İnternetten araştırma yapmamı veya makale okumamı ister misin?"
        elif any(app in app_title_lower for app in self.MEDIA_APPS):
            context_type = "media"
            suggestion = "Medya oynatılıyor. Spotify veya ses kontrolü eklentilerim hazır."
            
        return {
            "active_app": app_title,
            "context_type": context_type,
            "suggestion": suggestion,
            "timestamp": int(time.time())
        }

    def _monitor_loop(self):
        while self.running:
            try:
                context = self.analyze_context()
                current_app = context["active_app"]
                
                if current_app and current_app != self.last_app:
                    self.last_app = current_app
                    logger.info(f"Screen context changed: {current_app} ({context['context_type']})")
                    if self.on_context_change:
                        self.on_context_change(context)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            time.sleep(self.interval)

screen_monitor = ScreenMonitor()
