#!/usr/bin/env python3
"""
F.R.I.D.A.Y. — Arka Planda Çalışan Alkış ile Başlatıcı (Clap Launcher)
Sistem kapalıyken bile ellerinizi çırptığınızda ana uygulamayı otomatik başlatır.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
import numpy as np
import sounddevice as sd

# Alkış algılama ayarları
THRESHOLD = 26000        # Hassasiyet eşiği hafifçe artırıldı (Loud clap)
CHUNK_SIZE = 1024        # Mikrofon okuma boyutu
SAMPLE_RATE = 16000      # 16kHz
DEBOUNCE_TIME = 3.0      # İki başarılı çift alkış tetiklemesi arasındaki bekleme süresi
MIN_DOUBLE_CLAP_INTERVAL = 0.28  # İki alkış arasındaki minimum saniye (Refrakter kilit penceresi)
MAX_DOUBLE_CLAP_INTERVAL = 0.80  # İki alkış arasındaki maksimum saniye

BASE_DIR = Path(__file__).resolve().parent
LOCK_FILE = BASE_DIR / "friday.lock"

print("[CLAP LAUNCHER] Akilli Cift Alkis algilayici aktif. F.R.I.D.A.Y icin mikrofon dinleniyor...")

def is_friday_running() -> bool:
    # 1. Lock dosyası kontrolü (PID tabanlı ve psutil ile son derece kararlı)
    if LOCK_FILE.exists():
        try:
            content = LOCK_FILE.read_text(encoding="utf-8").strip()
            if content:
                pid = int(content)
                import psutil
                if psutil.pid_exists(pid):
                    return True
                else:
                    print(f"[CLAP LAUNCHER] [UYARI] Yetim lock dosyasi tespit edildi (PID: {pid} aktif degil). Temizleniyor...")
                    try:
                        LOCK_FILE.unlink()
                    except Exception:
                        pass
        except Exception:
            pass
    
    # 2. Windows tasklist kontrolü (ekstra güvenlik)
    try:
        output = subprocess.check_output('tasklist /FI "WINDOWTITLE eq F.R.I.D.A.Y"', shell=True, text=True)
        if "python" in output.lower() or "friday" in output.lower():
            return True
    except Exception:
        pass
    
    return False

last_peak_time = 0.0
last_activation_time = 0.0

def audio_callback(indata, frames, time_info, status):
    global last_peak_time, last_activation_time
    if status:
        pass
    
    if len(indata) > 0:
        peak = np.max(np.abs(indata))
        if peak > THRESHOLD:
            curr = time.time()
            # Debounce kontrolü: En son başarılı aktivasyondan sonra DEBOUNCE_TIME kadar bekle
            if curr - last_activation_time < DEBOUNCE_TIME:
                return

            # İki alkış arasındaki süreyi kontrol et
            diff = curr - last_peak_time
            if MIN_DOUBLE_CLAP_INTERVAL <= diff <= MAX_DOUBLE_CLAP_INTERVAL:
                # Çift alkış başarıyla tamamlandı!
                last_activation_time = curr
                last_peak_time = 0.0  # Sıfırla
                print(f"[CLAP LAUNCHER] [OK] Akilli CIFT ALKIS algilandi! Peak Genligi: {peak}")
                
                if not is_friday_running():
                    print("[CLAP LAUNCHER] [BASLATILIYOR] F.R.I.D.A.Y zaten calismiyor. Baslatiliyor...")
                    # main.py dosyasını yeni bir konsol penceresi açarak çalıştır
                    main_py_path = BASE_DIR / "main.py"
                    subprocess.Popen(
                        ["py", "-3", str(main_py_path)],
                        cwd=str(BASE_DIR),
                        creationflags=subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0
                    )
                else:
                    print("[CLAP LAUNCHER] [INFO] F.R.I.D.A.Y zaten arka planda veya on planda aktif.")
            else:
                # İlk alkış olarak kaydet veya eğer çok hızlı geldiyse (gürültü/kapı gıcırtısı/yankı) kaydır
                if diff < MIN_DOUBLE_CLAP_INTERVAL:
                    # Bu sürekli bir gürültüdür (kapı gıcırtısı, kapı sürgüsü tıkırtısı vb.)
                    # Başlangıç noktasını şimdiye kaydırarak araya temiz bir sessizlik girmesini şart koşuyoruz!
                    last_peak_time = curr
                else:
                    # Temiz bir sessizlik sonrası ilk alkış algılandı
                    print(f"[CLAP LAUNCHER] Birinci alkis algilandi (Peak: {peak}), ikinci bekleniyor...")
                    last_peak_time = curr

def main():
    try:
        # Eski çalışan tüm clap_launcher instances'larını temizle (Çakışmaları önlemek için)
        import psutil, os
        curr_pid = os.getpid()
        parent_pid = os.getppid() if hasattr(os, "getppid") else 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                cmd = proc.info['cmdline']
                # Yalnızca python veya pythonw yorumlayıcı süreçlerini sonlandır (powershell veya cmd terminal süreçlerini engellemek için)
                if 'python' in name:
                    if cmd and any('clap_launcher.py' in c for c in cmd):
                        # Kendi sürecimizi ve bizi başlatan ebeveyn süreci (örn. py.exe veya cmd.exe) asla sonlandırma
                        if proc.info['pid'] not in (curr_pid, parent_pid):
                            print(f"[CLAP LAUNCHER] [TEMIZLIK] Eski arka plan baslaticisi temizleniyor (PID: {proc.info['pid']})...")
                            try:
                                proc.kill()
                            except Exception:
                                proc.terminate()
            except Exception:
                pass
    except Exception:
        pass

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE, dtype='int16', callback=audio_callback):
            while True:
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[CLAP LAUNCHER] Durduruldu.")
    except Exception as e:
        print(f"[CLAP LAUNCHER] [HATA] Hata: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
