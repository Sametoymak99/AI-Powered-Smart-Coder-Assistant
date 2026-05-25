import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("SpotifyPlugin")

TOOL_DECLARATIONS = [
    {
        "name": "spotify_play",
        "description": "Spotify'ı açar ve belirtilen şarkı/sanatçıyı çalar ya da müzik duraklatılmışsa devam ettirir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Aranacak şarkı veya sanatçı adı (boş bırakılırsa çalmaya devam eder)."}
            }
        }
    },
    {
        "name": "spotify_pause",
        "description": "Spotify'da çalan müziği duraklatır.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "spotify_next",
        "description": "Sonraki şarkıya geçer.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "spotify_prev",
        "description": "Önceki şarkıya döner.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "spotify_volume",
        "description": "Spotify ses seviyesini ayarlar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level": {"type": "INTEGER", "description": "Ses yüzdesi (0-100)"}
            },
            "required": ["level"]
        }
    }
]

def _run_ps_command(cmd: str) -> str:
    try:
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
        return res.stdout
    except Exception as e:
        logger.error(f"PowerShell execution failed: {e}")
        return str(e)

def spotify_play(query: str = "") -> str:
    if query:
        # Search & Play via URI protocol handler
        cmd = f"Start-Process 'spotify:search:{query}'"
        _run_ps_command(cmd)
        # Give it a second to load, then send Play hotkey
        import time
        time.sleep(1.5)
        # Send Space to play the search result
        cmd_play = "$wshell = New-Object -ComObject wscript.shell; if ($wshell.AppActivate('Spotify')) { Sleep -m 500; $wshell.SendKeys(' ') }"
        _run_ps_command(cmd_play)
        return f"Spotify'da '{query}' arandı ve başlatıldı."
    else:
        # Send Media Play/Pause key (0xB3 is VK_MEDIA_PLAY_PAUSE)
        cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys([char]179)"
        _run_ps_command(cmd)
        return "Spotify müziği devam ettirildi (Media key)."

def spotify_pause() -> str:
    # Send Media Play/Pause key
    cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys([char]179)"
    _run_ps_command(cmd)
    return "Spotify müziği duraklatıldı."

def spotify_next() -> str:
    # Send Media Next key (0xB0 is VK_MEDIA_NEXT_TRACK = Char 176)
    cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys([char]176)"
    _run_ps_command(cmd)
    return "Sonraki şarkıya geçildi."

def spotify_prev() -> str:
    # Send Media Prev key (0xB1 is VK_MEDIA_PREV_TRACK = Char 177)
    cmd = "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys([char]177)"
    _run_ps_command(cmd)
    return "Önceki şarkıya geçildi."

def spotify_volume(level: int) -> str:
    # Using python volume adjust or windows master volume. Let's do windows master volume via pycaw
    try:
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
            if session.Process and session.Process.name().lower() == "spotify.exe":
                volume.SetMasterVolume(float(level) / 100.0, None)
                return f"Spotify ses seviyesi %{level} yapıldı."
        return "Spotify çalışırken bulunamadı."
    except Exception as e:
        logger.error(f"pycaw volume adjustment failed: {e}")
        return f"Ses ayarı başarısız: {e}"

HANDLERS = {
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_next": spotify_next,
    "spotify_prev": spotify_prev,
    "spotify_volume": spotify_volume
}
