"""
Uygulama açma — Windows + macOS çapraz platform desteği
Samet Omak tarafından güncellendi
"""

import subprocess
import shutil
import platform
import os
import sys
import signal


# Windows uygulama eşlemeleri
WIN_APP_ALIASES = {
    # Tarayıcılar
    "chrome":           "chrome",
    "google chrome":    "chrome",
    "firefox":          "firefox",
    "edge":             "msedge",
    "microsoft edge":   "msedge",
    "opera":            "opera",

    # Geliştirici
    "vscode":           "code",
    "vs code":          "code",
    "code":             "code",
    "terminal":         "wt",  # Windows Terminal
    "powershell":       "powershell",
    "cmd":              "cmd",
    "komut istemi":     "cmd",
    "notepad":          "notepad",
    "notepad++":        "notepad++",

    # Sistem
    "görev yöneticisi":       "taskmgr",
    "task manager":           "taskmgr",
    "ayarlar":                "ms-settings:",
    "settings":               "ms-settings:",
    "denetim masası":         "control",
    "control panel":          "control",
    "dosya gezgini":          "explorer",
    "file explorer":          "explorer",
    "explorer":               "explorer",
    "disk temizleme":         "cleanmgr",
    "registry":               "regedit",
    "kayıt defteri":          "regedit",
    "sistem bilgisi":         "msinfo32",
    "system info":            "msinfo32",
    "aygıt yöneticisi":       "devmgmt.msc",
    "device manager":         "devmgmt.msc",
    "olay görüntüleyicisi":   "eventvwr",
    "event viewer":           "eventvwr",
    "servisler":              "services.msc",
    "services":               "services.msc",

    # Ofis / Microsoft
    "word":             "winword",
    "excel":            "excel",
    "powerpoint":       "powerpnt",
    "outlook":          "outlook",
    "onenote":          "onenote",
    "teams":            "teams",
    "microsoft teams":  "teams",

    # Medya
    "spotify":          "spotify",
    "vlc":              "vlc",
    "media player":     "wmplayer",
    "windows media player": "wmplayer",
    "groove":           "mswindowsmusic",
    "fotoğraflar":      "ms-photos:",
    "photos":           "ms-photos:",

    # İletişim
    "discord":          "discord",
    "telegram":         "telegram",
    "whatsapp":         "whatsapp",
    "slack":            "slack",
    "zoom":             "zoom",
    "skype":            "skype",

    # Araçlar
    "hesap makinesi":   "calc",
    "calculator":       "calc",
    "paint":            "mspaint",
    "snipping tool":    "snippingtool",
    "ekran alıntısı":   "snippingtool",
    "not defteri":      "notepad",
    "wordpad":          "wordpad",
    "3d viewer":        "3dviewer",
    "kamera":           "microsoft.windows.camera:",
    "camera":           "microsoft.windows.camera:",
    "saat":             "ms-clock:",
    "clock":            "ms-clock:",
    "takvim":           "outlookcal:",
    "calendar":         "outlookcal:",
    "haritalar":        "bingmaps:",
    "maps":             "bingmaps:",
    "hava durumu":      "bingweather:",
    "weather":          "bingweather:",
    "mağaza":           "ms-windows-store:",
    "store":            "ms-windows-store:",
    "xbox":             "xbox:",

    # Geliştirme
    "docker":           "docker desktop",
    "postman":          "postman",
    "git bash":         "git-bash",
    "github desktop":   "github desktop",
    "pycharm":          "pycharm",
    "intellij":         "idea",
    "android studio":   "studio64",
    "figma":            "figma",

    # Oyun
    "steam":            "steam",
    "epic games":       "epicgameslauncher",
    "battle.net":       "battle.net",
}

# macOS uygulama eşlemeleri (önceki kod)
MAC_APP_ALIASES = {
    "safari":           "Safari",
    "chrome":           "Google Chrome",
    "firefox":          "Firefox",
    "terminal":         "Terminal",
    "iterm":            "iTerm",
    "iterm2":           "iTerm",
    "finder":           "Finder",
    "spotify":          "Spotify",
    "vscode":           "Visual Studio Code",
    "vs code":          "Visual Studio Code",
    "code":             "Visual Studio Code",
    "xcode":            "Xcode",
    "notion":           "Notion",
    "slack":            "Slack",
    "discord":          "Discord",
    "whatsapp":         "WhatsApp",
    "telegram":         "Telegram",
    "zoom":             "zoom.us",
    "mail":             "Mail",
    "calendar":         "Calendar",
    "takvim":           "Calendar",
    "notes":            "Notes",
    "notlar":           "Notes",
    "music":            "Music",
    "müzik":            "Music",
    "photos":           "Photos",
    "fotoğraflar":      "Photos",
    "maps":             "Maps",
    "haritalar":        "Maps",
    "calculator":       "Calculator",
    "hesap makinesi":   "Calculator",
    "system preferences": "System Preferences",
    "system settings":  "System Settings",
    "ayarlar":          "System Settings",
    "activity monitor": "Activity Monitor",
    "aktivite monitörü": "Activity Monitor",
    "preview":          "Preview",
    "önizleme":         "Preview",
    "textedit":         "TextEdit",
    "numbers":          "Numbers",
    "pages":            "Pages",
    "keynote":          "Keynote",
    "figma":            "Figma",
    "postman":          "Postman",
    "docker":           "Docker",
    "sequel pro":       "Sequel Pro",
    "tableplus":        "TablePlus",
}


def _open_windows(app_name: str) -> str:
    """Windows'ta uygulama açar."""
    normalized = app_name.lower().strip()
    resolved = WIN_APP_ALIASES.get(normalized, app_name)

    # ms- veya diğer URI protokolleri (ms-settings: gibi)
    if ":" in resolved and not os.path.sep in resolved:
        try:
            os.startfile(resolved)
            return f"{app_name} açıldı."
        except Exception:
            pass
            
    # WhatsApp (UWP) URI protokolü ile açmayı dene
    if normalized == "whatsapp":
        try:
            os.startfile("whatsapp://")
            return "WhatsApp açıldı."
        except Exception:
            pass

    # Önce shutil.which ile PATH'te ara
    exe = shutil.which(resolved) or shutil.which(resolved + ".exe")
    if exe:
        try:
            subprocess.Popen(
                [exe],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
            return f"{app_name} açıldı."
        except Exception as e:
            return f"Hata: {e}"



    # Program Files klasörlerinde ara
    search_dirs = [
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        os.environ.get("LOCALAPPDATA", ""),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    ]
    for base in search_dirs:
        if not base or not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower().endswith(".exe") and normalized in f.lower():
                    full_path = os.path.join(root, f)
                    try:
                        subprocess.Popen(
                            [full_path],
                            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                            close_fds=True,
                        )
                        return f"{app_name} açıldı ({f})."
                    except Exception:
                        pass

    # Başlat menüsü ve Masaüstündeki kısayollarda (.lnk ve .url) ara
    start_menus = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.environ.get("PUBLIC", "") + r"\Desktop",
        os.environ.get("USERPROFILE", "") + r"\Desktop",
    ]
    for menu in start_menus:
        if not menu or not os.path.isdir(menu):
            continue
        for root, dirs, files in os.walk(menu):
            for f in files:
                if f.lower().endswith(".lnk") or f.lower().endswith(".url"):
                    norm_clean = normalized.replace(" ", "").replace("-", "")
                    target_clean = f.lower().replace(" ", "").replace("-", "")
                    if norm_clean in target_clean:
                        full_path = os.path.join(root, f)
                        try:
                            os.startfile(full_path)
                            return f"{app_name} açıldı ({f})."
                        except Exception:
                            pass

    # start komutu ile dene (Windows shell built-in) - Son çare
    try:
        subprocess.Popen(
            f'start "" "{resolved}"',
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        return f"{app_name} açılıyor... (Eğer açılmazsa yüklü olduğundan emin olun)"
    except Exception:
        pass

    return f"'{app_name}' bulunamadı veya açılamadı. Uygulama yüklü ve PATH'te olduğundan emin olun."


def _open_macos(app_name: str) -> str:
    """macOS'ta uygulama açar."""
    normalized = app_name.lower().strip()
    resolved   = MAC_APP_ALIASES.get(normalized, app_name)

    try:
        result = subprocess.run(
            ["open", "-a", resolved],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return f"{resolved} açıldı."
        else:
            result2 = subprocess.run(
                ["open", resolved],
                capture_output=True, text=True, timeout=10
            )
            if result2.returncode == 0:
                return f"{app_name} açıldı."
            return f"'{app_name}' bulunamadı veya açılamadı."
    except subprocess.TimeoutExpired:
        return f"'{app_name}' açılırken zaman aşımı."
    except Exception as e:
        return f"Hata: {e}"


def open_app(app_name: str) -> str:
    """Uygulamayı açar, başarı/hata mesajı döndürür."""
    if not app_name:
        return "Uygulama adı belirtilmedi."

    system = platform.system()
    if system == "Windows":
        return _open_windows(app_name)
    elif system == "Darwin":
        return _open_macos(app_name)
    else:
        # Linux fallback
        normalized = app_name.lower().strip()
        exe = shutil.which(normalized)
        if exe:
            try:
                subprocess.Popen([exe], close_fds=True)
                return f"{app_name} açıldı."
            except Exception as e:
                return f"Hata: {e}"
        try:
            subprocess.Popen(["xdg-open", app_name], close_fds=True)
            return f"{app_name} açılıyor..."
        except Exception as e:
            return f"Hata: {e}"


def list_running_apps() -> str:
    """Çalışan uygulamaları listeler (Windows)."""
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
                 "Select-Object -ExpandProperty ProcessName | Sort-Object -Unique"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                procs = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
                return "Çalışan uygulamalar: " + ", ".join(procs[:20])
            return "Çalışan uygulama listesi alınamadı."
        except Exception as e:
            return f"Hata: {e}"
    elif system == "Darwin":
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of every process whose background only is false'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return "Çalışan uygulamalar: " + result.stdout.strip()
        except Exception:
            pass
        return "Uygulama listesi alınamadı."
    return "Bu platform desteklenmiyor."


def kill_app(app_name: str) -> str:
    """Çalışan bir uygulamayı kapatır (Windows)."""
    if not app_name:
        return "Uygulama adı belirtilmedi."

    system = platform.system()
    normalized = app_name.lower().strip()

    # Alias'tan gerçek exe adını al
    resolved = WIN_APP_ALIASES.get(normalized, app_name)
    exe_name = os.path.basename(resolved).replace(".exe", "")

    if system == "Windows":
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", f"{exe_name}.exe"],
                capture_output=True, text=True, timeout=8
            )
            if result.returncode == 0:
                return f"{app_name} kapatıldı."
            # process name olarak dene
            result2 = subprocess.run(
                ["taskkill", "/F", "/IM", f"{app_name}.exe"],
                capture_output=True, text=True, timeout=8
            )
            if result2.returncode == 0:
                return f"{app_name} kapatıldı."
            return f"'{app_name}' kapatılamadı veya zaten çalışmıyor."
        except Exception as e:
            return f"Hata: {e}"
    elif system == "Darwin":
        try:
            result = subprocess.run(
                ["pkill", "-x", app_name],
                capture_output=True, text=True, timeout=8
            )
            return f"{app_name} kapatıldı." if result.returncode == 0 else f"'{app_name}' bulunamadı."
        except Exception as e:
            return f"Hata: {e}"
    return "Bu platform desteklenmiyor."
