"""
TTS (Text-to-Speech) — Cross-platform support
On Windows: Uses SAPI (Speech API) via comtypes.
On macOS: Uses the built-in 'say' command.
On Linux: Uses 'espeak'.
"""

import sys
import os
import subprocess
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger("TTS")

# Windows SAPI Setup
_voice = None
if sys.platform == "win32":
    try:
        import comtypes.client
        # Initialize COM library for the thread if not initialized
        try:
            comtypes.CoInitialize()
        except Exception:
            pass
        _voice = comtypes.client.CreateObject("SAPI.SpVoice")
    except Exception as e:
        logger.error(f"Failed to initialize SAPI SpVoice on Windows: {e}")

def speak_text(text: str, on_done: Optional[Callable[[], None]] = None, blocking: bool = False):
    """
    Metni sesli olarak okur.
    on_done: okuma bitince çağrılacak fonksiyon (opsiyonel)
    blocking: True ise bitene kadar bekler
    """
    if not text or not text.strip():
        if on_done:
            on_done()
        return

    # Çok uzun metinleri kısalt
    max_len = 500
    if len(text) > max_len:
        text = text[:max_len] + "..."

    def _run():
        if sys.platform == "win32" and _voice:
            try:
                # Initialize COM for the background thread
                try:
                    comtypes.CoInitialize()
                except Exception:
                    pass
                # SAPI SpVoice Speak flags: 0 is default (synchronous), 1 is asynchronous
                # We can run synchronously in this thread since it's already a background thread
                _voice.Speak(text)
            except Exception as e:
                logger.error(f"SAPI speak failed: {e}")
        elif sys.platform == "darwin":
            try:
                subprocess.run(["say", text], check=False)
            except Exception as e:
                logger.error(f"macOS say command failed: {e}")
        else:
            try:
                subprocess.run(["espeak", text], check=False)
            except Exception as e:
                logger.error(f"Linux espeak command failed: {e}")
                
        if on_done:
            on_done()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, name="TTS-Thread", daemon=True).start()

def get_available_voices() -> list[str]:
    """Mevcut sistem seslerini listeler."""
    voices = []
    if sys.platform == "win32" and _voice:
        try:
            for v in _voice.GetVoices():
                voices.append(v.GetDescription())
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if line.strip():
                    voices.append(line.split()[0])
        except Exception:
            pass
    return voices
