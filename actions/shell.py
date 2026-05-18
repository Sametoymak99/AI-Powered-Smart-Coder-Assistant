"""
Terminal komutu çalıştırma — macOS bash
Alp Ünlü tarafından yapılmıştır — @alppunlu
"""

import subprocess


# Tehlikeli komutları engelle
BLOCKED = [
    "format",
    "del /s /q /f c:\\",
    "remove-item c:\\ -recurse -force",
    "stop-computer"
]


def shell_run(command: str, timeout: int = 45) -> str:
    if not command:
        return "Komut belirtilmedi."

    cmd_lower = command.lower()
    stripped = command.strip()

    for blocked in BLOCKED:
        if blocked in cmd_lower:
            return f"Güvenlik: Bu komut engellendi → {blocked}"

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=timeout
        )
        output = (result.stdout + result.stderr).strip()
        if not output:
            if result.returncode == 0:
                return "Komut başarıyla çalıştı (çıktı yok)."
            else:
                return f"Komut hatayla sonlandı (Kod: {result.returncode})"
                
        # Çok uzun çıktıları kırp
        if len(output) > 2000:
            output = output[:2000] + "\n... (çıktı kısaltıldı)"
        return output
    except subprocess.TimeoutExpired:
        return f"Komut zaman aşımına uğradı ({timeout}s)."
    except Exception as e:
        return f"Hata: {e}"
