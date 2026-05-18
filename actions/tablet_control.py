"""
actions/tablet_control.py — ADB üzerinden Android tablet kontrolü
"""
import subprocess

# Sık kullanılan uygulama paket adları haritası
APP_MAPPINGS = {
    "youtube": "com.google.android.youtube",
    "spotify": "com.spotify.music",
    "netflix": "com.netflix.mediaclient",
    "chrome": "com.android.chrome",
    "instagram": "com.instagram.android",
    "whatsapp": "com.whatsapp",
    "galeri": "com.android.gallery3d", # Cihaza göre değişebilir
    "ayarlar": "com.android.settings",
    "hesap makinesi": "com.android.calculator2",
    "haritalar": "com.google.android.apps.maps",
}

def run_adb_command(command: list[str]) -> tuple[bool, str]:
    """ADB komutunu çalıştırır."""
    try:
        # İndirdiğimiz ADB'nin tam yolu
        adb_path = r"c:\Users\samet\OneDrive\Masaüstü\jarvis\platform-tools\adb.exe"
        result = subprocess.run([adb_path] + command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except FileNotFoundError:
        return False, "ADB bulunamadı. Lütfen indirildiğinden emin olun."
    except Exception as e:
        return False, f"Hata: {str(e)}"

def open_tablet_app(app_name_or_package: str) -> str:
    """Tablette uygulama açar."""
    package = APP_MAPPINGS.get(app_name_or_package.lower(), app_name_or_package)
    
    # Monkey aracı ile launcher aktivitesini tetikleme (en kolay yol)
    success, output = run_adb_command(["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"])
    
    if success:
        return f"Tablet üzerinde '{app_name_or_package}' uygulaması açıldı."
    else:
        return f"Uygulama açılamadı: {output}"

def close_tablet_app(app_name_or_package: str) -> str:
    """Tablette uygulama kapatır."""
    package = APP_MAPPINGS.get(app_name_or_package.lower(), app_name_or_package)
    success, output = run_adb_command(["shell", "am", "force-stop", package])
    
    if success:
        return f"Tablet üzerinde '{app_name_or_package}' uygulaması kapatıldı."
    else:
        return f"Uygulama kapatılamadı: {output}"

def press_tablet_key(key_code: str) -> str:
    """Tablette tuş basma simüle eder (Örn: 3=Home, 4=Back)."""
    success, output = run_adb_command(["shell", "input", "keyevent", key_code])
    if success:
        return f"Tablet tuş komutu ({key_code}) başarılı."
    else:
        return f"Tuş komutu başarısız: {output}"

def check_connection() -> str:
    """Bağlı cihazları listeler."""
    success, output = run_adb_command(["devices"])
    if success:
        return f"Bağlı cihazlar:\n{output}"
    else:
        return f"Bağlantı kontrolü başarısız: {output}"
