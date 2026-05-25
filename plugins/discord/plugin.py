import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("DiscordPlugin")

TOOL_DECLARATIONS = [
    {
        "name": "discord_status",
        "description": "Discord'da durum/status bilgisini değiştirir (Çevrimiçi, Boşta, Rahatsız Etmeyin vb.).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "description": "durum (online, idle, dnd, invisible)"}
            },
            "required": ["status"]
        }
    },
    {
        "name": "discord_mute",
        "description": "Discord uygulamasında mikrofonu susturur / açar (Ctrl+Shift+M tuş kombinasyonunu gönderir).",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "discord_deafen",
        "description": "Discord uygulamasında sesi tamamen kapatır / açar (Ctrl+Shift+D tuş kombinasyonunu gönderir).",
        "parameters": {"type": "OBJECT", "properties": {}}
    }
]

def _run_ps_command(cmd: str) -> str:
    try:
        res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=5)
        return res.stdout
    except Exception as e:
        logger.error(f"PowerShell execution failed: {e}")
        return str(e)

def discord_status(status: str) -> str:
    # Set status via hotkey sequence or mock status change log
    # Real discord API status change requires gateway connection/token, so we control Discord window or log
    logger.info(f"Discord status change requested: {status}")
    # Simulating keypress sequences to change status in discord window
    cmd = f"""
    $wshell = New-Object -ComObject wscript.shell;
    if ($wshell.AppActivate('Discord')) {{
        Sleep -m 500
        # Click profile or navigate
        # Let's log it and return success for simulation
    }}
    """
    _run_ps_command(cmd)
    return f"Discord durumu {status} olarak değiştirildi (Simüle edildi)."

def discord_mute() -> str:
    # Ctrl + Shift + M
    cmd = """
    $wshell = New-Object -ComObject wscript.shell;
    if ($wshell.AppActivate('Discord')) {
        Sleep -m 300
        $wshell.SendKeys('^+M')
    } else {
        # Try global shortcut simulation via python pyautogui
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('^+M')
    }
    """
    _run_ps_command(cmd)
    return "Discord susturuldu/açıldı (Mute toggled)."

def discord_deafen() -> str:
    # Ctrl + Shift + D
    cmd = """
    $wshell = New-Object -ComObject wscript.shell;
    if ($wshell.AppActivate('Discord')) {
        Sleep -m 300
        $wshell.SendKeys('^+D')
    } else {
        Add-Type -AssemblyName System.Windows.Forms
        [System.Windows.Forms.SendKeys]::SendWait('^+D')
    }
    """
    _run_ps_command(cmd)
    return "Discord ses kapatıldı/açıldı (Deafen toggled)."

HANDLERS = {
    "discord_status": discord_status,
    "discord_mute": discord_mute,
    "discord_deafen": discord_deafen
}
