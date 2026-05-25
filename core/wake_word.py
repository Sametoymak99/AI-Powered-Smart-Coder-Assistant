import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("WakeWordDetector")

class WakeWordDetector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WakeWordDetector, cls).__new__(cls)
            cls._instance._init_detector()
        return cls._instance

    def _init_detector(self):
        self.WAKE_WORDS = ["friday", "hey friday", "ay friday", "freeday", "fridey"]
        self.running = False
        self.callback: Optional[Callable[[], None]] = None
        self._thread: Optional[threading.Thread] = None

    def start(self, callback: Callable[[], None]):
        if self.running:
            return
        self.callback = callback
        self.running = True
        self._thread = threading.Thread(target=self._listen_loop, name="WakeWord-Listener", daemon=True)
        self._thread.start()
        logger.info("Wake word detector started.")

    def stop(self):
        self.running = False
        logger.info("Wake word detector stopped.")

    def _listen_loop(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        
        # Adjust threshold for ambient noise
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            logger.error(f"Could not open microphone for noise adjustment: {e}")
            self.running = False
            return

        while self.running:
            try:
                with sr.Microphone() as source:
                    # Listen for a brief moment to catch a word
                    audio = r.listen(source, timeout=3, phrase_time_limit=3)
                    
                # Recognize offline/online using sphinx or google (Google is faster and accurate)
                text = r.recognize_google(audio, language="en-US").lower()
                logger.info(f"WakeWord candidate text: {text}")
                
                if any(ww in text for ww in self.WAKE_WORDS):
                    logger.info("Wake word DETECTED!")
                    if self.callback:
                        self.callback()
                        
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except Exception as e:
                logger.error(f"Error in wake word loop: {e}")
                time.sleep(1)

wake_word = WakeWordDetector()
