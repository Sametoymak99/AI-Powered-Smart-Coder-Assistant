"""
Gelişmiş Oyun Desteği — F.R.I.D.A.Y. Pro Oyun Asistanı
- Steam kütüphanesini tarayarak oyunları doğrudan isminden başlatabilme.
- Auto-Clicker (Tıklama makrosu), Mouse Sürükleme ve Sol/Sağ Tık Basılı Tutma.
- Klavye tuş dizileri ve Tuş Basılı Tutma makroları.
- Ekran Ortasında Özelleştirilebilir Nişangah (Dot, Cross, Circle, T-Shape stilleri).
- Oyun Performans Güçlendirici (Game Booster - CPU Öncelik Ayarlama).
"""

import os
import subprocess
import time
import re
import threading
import tkinter as tk
import pyautogui

# Crosshair overlay penceresi referansı
_crosshair_window = None
# Güçlendirilen oyunun adı
_boosted_game = None
# Öncelikleri düşürülen arka plan uygulamalarını tutar
_prioritized_apps = {}

def get_game_helper_status() -> dict:
    """Oyun asistanının o anki durumunu (nişangah aktifliği, güçlendirilen oyun) döndürür."""
    global _crosshair_window, _boosted_game
    return {
        "crosshair_active": _crosshair_window is not None,
        "boosted_game": _boosted_game
    }

def get_installed_steam_games() -> dict[str, str]:
    """Sistemdeki tüm yüklü Steam oyunlarının adını ve App ID'sini bulur."""
    games = {}
    steam_paths = [
        r"C:\Program Files (x86)\Steam\steamapps",
        r"C:\Program Files\Steam\steamapps",
        r"D:\SteamLibrary\steamapps",
        r"E:\SteamLibrary\steamapps"
    ]
    
    for path in steam_paths:
        if os.path.exists(path):
            try:
                for file in os.listdir(path):
                    if file.startswith("appmanifest_") and file.endswith(".acf"):
                        acf_path = os.path.join(path, file)
                        try:
                            with open(acf_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                appid_match = re.search(r'"appid"\s+"(\d+)"', content)
                                name_match = re.search(r'"name"\s+"([^"]+)"', content)
                                if appid_match and name_match:
                                    appid = appid_match.group(1)
                                    name = name_match.group(1)
                                    games[name.lower()] = appid
                        except Exception:
                            pass
            except Exception:
                pass
    return games

def launch_steam_game(game_name: str) -> str:
    """Steam oyununu isminden arayarak başlatır."""
    games = get_installed_steam_games()
    normalized_query = game_name.lower().strip()
    
    found_appid = None
    matched_game_name = ""
    for name, appid in games.items():
        if normalized_query in name:
            found_appid = appid
            matched_game_name = name
            break
            
    if found_appid:
        try:
            os.startfile(f"steam://run/{found_appid}")
            return f"✅ '{matched_game_name.title()}' (Steam AppID: {found_appid}) başlatılıyor..."
        except Exception as e:
            return f"Hata: Oyun başlatılamadı: {e}"
            
    from actions.open_app import open_app
    return open_app(game_name)

# ── MAKROLAR VE KLAVYE/FARE OTOMASYONU ────────────────────────────────────────

def auto_clicker(clicks_per_second: int, duration_seconds: int) -> str:
    """Belirtilen süre boyunca saniyede X kez tıklar (Ayrı thread içinde çalışır)."""
    def click_loop():
        delay = 1.0 / clicks_per_second
        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            pyautogui.click()
            time.sleep(delay)
            
    thread = threading.Thread(target=click_loop)
    thread.daemon = True
    thread.start()
    return f"🚀 Saniyede {clicks_per_second} tıklamalı makro {duration_seconds} saniye için başlatıldı."

def hold_click(button: str = "left", duration: float = 3.0) -> str:
    """Belirtilen fare tuşunu belirli bir süre basılı tutar (örn: madencilik veya şarjlı atışlar için)."""
    def hold_loop():
        pyautogui.mouseDown(button=button)
        time.sleep(duration)
        pyautogui.mouseUp(button=button)
        
    thread = threading.Thread(target=hold_loop)
    thread.daemon = True
    thread.start()
    return f"🖱️ Fare '{button}' tuşu {duration} saniye boyunca basılı tutuluyor..."

def hold_key(key: str, duration: float = 3.0) -> str:
    """Klavyeden bir tuşu (örn: 'w', 'shift', 'space') belirtilen süre boyunca basılı tutar."""
    def hold_loop():
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
        
    thread = threading.Thread(target=hold_loop)
    thread.daemon = True
    thread.start()
    return f"⌨️ Klavye '{key}' tuşu {duration} saniye boyunca basılı tutuluyor..."

def press_keys_sequence(sequence: str, delay: float = 0.5) -> str:
    """Virgülle ayrılmış bir tuş dizisini sırayla basar (örn: 'q,w,e,r' veya skill komboları)."""
    def seq_loop():
        keys = [k.strip() for k in sequence.split(",")]
        for key in keys:
            if "+" in key:
                parts = [p.strip() for p in key.split("+")]
                pyautogui.hotkey(*parts)
            else:
                pyautogui.press(key)
            time.sleep(delay)
            
    thread = threading.Thread(target=seq_loop)
    thread.daemon = True
    thread.start()
    return f"⌨️ '{sequence}' tuş dizisi {delay} sn aralıklarla basılıyor..."

# ── GELİŞMİŞ NİŞANGAH OVERLAY (CROSSHAIR) ─────────────────────────────────────

def toggle_crosshair(color: str = "red", size: int = 12, style: str = "dot") -> str:
    """
    Ekranın tam ortasında şeffaf bir nişangah açar veya kapatır.
    Stiller: 'dot' (nokta), 'cross' (artı +), 'circle' (boş çember), 't_shape' (T şeklinde).
    """
    global _crosshair_window
    
    if _crosshair_window is not None:
        try:
            _crosshair_window.destroy()
        except Exception:
            pass
        _crosshair_window = None
        return "❌ Ekran ortasındaki nişangah kapatıldı."
        
    try:
        root = tk.Tk()
        _crosshair_window = root
        
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", "black")
        root.config(bg="black")
        
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        
        x = (screen_w // 2) - (size // 2)
        y = (screen_h // 2) - (size // 2)
        
        root.geometry(f"{size}x{size}+{x}+{y}")
        
        canvas = tk.Canvas(root, width=size, height=size, bg="black", highlightthickness=0)
        canvas.pack()
        
        # Seçilen stile göre çiz
        if style == "dot":
            canvas.create_oval(2, 2, size - 2, size - 2, fill=color, outline="")
        elif style == "cross":
            mid = size // 2
            # Yatay çizgi
            canvas.create_line(0, mid, size, mid, fill=color, width=2)
            # Dikey çizgi
            canvas.create_line(mid, 0, mid, size, fill=color, width=2)
        elif style == "circle":
            canvas.create_oval(1, 1, size - 1, size - 1, outline=color, width=2)
            # Merkez nokta
            mid = size // 2
            canvas.create_oval(mid-1, mid-1, mid+1, mid+1, fill=color, outline="")
        elif style == "t_shape":
            mid = size // 2
            # Yatay çizgi
            canvas.create_line(0, mid, size, mid, fill=color, width=2)
            # Alt dikey çizgi
            canvas.create_line(mid, mid, mid, size, fill=color, width=2)
            
        def run_tk():
            root.mainloop()
            
        t = threading.Thread(target=run_tk)
        t.daemon = True
        t.start()
        
        return f"🎯 Ekran ortasında '{style}' tarzı nişangah ({color}, boyut: {size}px) açıldı!"
    except Exception as e:
        _crosshair_window = None
        return f"Hata: Nişangah oluşturulamadı: {e}"

# ── GAME BOOSTER (İŞLEMCİ ÖNCELİK GÜÇLENDİRİCİ) ───────────────────────────────

def boost_game_performance(game_process_name: str) -> str:
    """
    Oyunun işlemci önceliğini Yüksek (High) yapar.
    Aynı zamanda arka plandaki ağır tarayıcıları (Chrome, Edge vb.) Düşük önceliğe alarak oyuna alan açar.
    """
    global _boosted_game
    if not game_process_name.endswith(".exe"):
        game_process_name += ".exe"
        
    try:
        # Oyuna Yüksek Öncelik ver
        cmd_game = f'powershell -Command "Get-Process -Name \'{game_process_name.replace(".exe", "")}\' -ErrorAction SilentlyContinue | foreach {{ $_.PriorityClass = \'High\' }}"'
        subprocess.run(cmd_game, shell=True, capture_output=True)
        
        # Arka plandaki ağır tarayıcıların önceliğini Idle (Düşük) yap
        heavy_apps = ["chrome", "msedge", "firefox", "steamwebhelper"]
        for app in heavy_apps:
            cmd_bg = f'powershell -Command "Get-Process -Name \'{app}\' -ErrorAction SilentlyContinue | foreach {{ $_.PriorityClass = \'Idle\' }}"'
            subprocess.run(cmd_bg, shell=True, capture_output=True)
            
        _boosted_game = game_process_name
        return f"🚀 Game Booster Aktif! '{game_process_name}' işlem önceliği Yüksek (High) yapıldı. Tarayıcılar Düşük (Idle) seviyeye çekilerek CPU yükü azaltıldı."
    except Exception as e:
        return f"Booster çalıştırılırken hata: {e}"

def restore_priorities() -> str:
    """Tüm arka plan uygulamalarının ve oyunların işlemci önceliğini normale çeker."""
    global _boosted_game
    try:
        apps = ["chrome", "msedge", "firefox", "steamwebhelper"]
        for app in apps:
            cmd = f'powershell -Command "Get-Process -Name \'{app}\' -ErrorAction SilentlyContinue | foreach {{ $_.PriorityClass = \'Normal\' }}"'
            subprocess.run(cmd, shell=True, capture_output=True)
        _boosted_game = None
        return "✅ Tüm sistem ve tarayıcı öncelikleri normale döndürüldü."
    except Exception as e:
        return f"Hata: Öncelikler sıfırlanamadı: {e}"

# ── AUTOPLAY & BOT ASİSTANLARI ───────────────────────────────────────────────

# Triggerbot aktif/durdur bayrağı
_triggerbot_active = False

# ── Oyun Önayarları ─────────────────────────────────────────────────────────
# Her oyunun düşman rengi için HSV aralıkları (H:0-179, S:0-255, V:0-255)
# Kırmızı HSV'de 0-10 ve 170-179 arasında (dairesel)
GAME_PRESETS = {
    # CS2 / CSGO — kırmızı düşman ismi + sağlık barı
    "cs2":     {"h_ranges": [(0, 8), (172, 179)], "s_min": 140, "v_min": 100, "pixel_threshold": 8},
    "csgo":    {"h_ranges": [(0, 8), (172, 179)], "s_min": 140, "v_min": 100, "pixel_threshold": 8},
    # Valorant — parlak kırmızı düşman outline
    "valorant":{"h_ranges": [(0, 10), (170, 179)], "s_min": 160, "v_min": 120, "pixel_threshold": 6},
    # Apex Legends — kırmızı isim + turuncu
    "apex":    {"h_ranges": [(0, 15), (168, 179)], "s_min": 130, "v_min": 100, "pixel_threshold": 10},
    # PUBG — kırmızı hasar sayısı / isimler
    "pubg":    {"h_ranges": [(0, 12), (168, 179)], "s_min": 120, "v_min": 90,  "pixel_threshold": 12},
    # Fortnite — mavi/mor düşman outline
    "fortnite":{"h_ranges": [(110, 140)],          "s_min": 150, "v_min": 100, "pixel_threshold": 8},
    # Genel kırmızı algılama (varsayılan)
    "red":     {"h_ranges": [(0, 12), (168, 179)], "s_min": 100, "v_min": 80,  "pixel_threshold": 5},
    # Sarı (bazı oyunlarda isim rengi)
    "yellow":  {"h_ranges": [(20, 35)],            "s_min": 150, "v_min": 150, "pixel_threshold": 8},
    # Beyaz (parlak hitbox/outline)
    "white":   {"h_ranges": [(0, 179)],            "s_min": 0,   "v_min": 230, "pixel_threshold": 15},
    # Evrensel — herhangi doygun renk
    "any":     {"h_ranges": [(0, 179)],            "s_min": 100, "v_min": 80,  "pixel_threshold": 20},
}


def _detect_color_cv2(img_bgr, preset: dict) -> tuple[bool, int]:
    """
    OpenCV cv2.cvtColor ile doğru ve hızlı HSV renk tespiti.
    img_bgr: numpy uint8 array (H, W, 3) BGR formatında (mss çıktısı)
    Döndürür: (tespit edildi mi, eşleşen piksel sayısı)
    """
    try:
        import cv2
        import numpy as np

        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        h = hsv[:, :, 0]
        s = hsv[:, :, 1]
        v = hsv[:, :, 2]

        s_min   = preset["s_min"]
        v_min   = preset["v_min"]
        threshold = preset["pixel_threshold"]

        sv_mask = (s >= s_min) & (v >= v_min)
        h_mask  = np.zeros(h.shape, dtype=bool)
        for h_lo, h_hi in preset["h_ranges"]:
            h_mask |= (h >= h_lo) & (h <= h_hi)

        count = int(np.count_nonzero(sv_mask & h_mask))
        return count >= threshold, count

    except Exception:
        return False, 0


def _detect_color_numpy(img_array, preset: dict) -> bool:
    """Eski RGB giriş uyumluluğu için sarmalayıcı — BGR'ye çevirip cv2 versiyonuna iletir."""
    try:
        import numpy as np
        bgr = img_array[:, :, ::-1].copy()   # RGB → BGR
        found, _ = _detect_color_cv2(bgr, preset)
        return found
    except Exception:
        return False


def _fast_left_click() -> None:
    """ctypes ile doğrudan WinAPI mouse_event — pyautogui'den çok daha düşük gecikme."""
    import ctypes
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP   = 0x0004
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP,   0, 0, 0, 0)


def triggerbot_color_change(
    duration: float = 60.0,
    scan_zone: int = 400,
    game: str = "red",
    fire_delay: float = 0.03,
    cooldown: float = 0.08,
    full_screen: bool = False,
) -> str:
    """
    PRO Triggerbot v2 — mss + cv2 HSV + ctypes tıklama ile ultra düşük gecikme.

    Parametreler:
      duration   — Botun aktif kalacağı saniye (varsayılan 60s)
      scan_zone  — Merkez etrafında taranacak yarıçap (px). full_screen=True ise yoksayılır.
      game       — Oyun önayarı: 'cs2', 'valorant', 'apex', 'pubg', 'fortnite', 'red', 'yellow', 'white', 'any'
      fire_delay — Tespit ile tıklama arasındaki gecikme sn (varsayılan 0.03 = 30ms)
      cooldown   — Art arda atış engeli süresi sn (varsayılan 0.08 = 80ms)
      full_screen— True ise tüm ekranı tara, False ise merkez ±scan_zone alanı
    """
    global _triggerbot_active

    if _triggerbot_active:
        _triggerbot_active = False
        return "⛔ Triggerbot durduruldu."

    preset = GAME_PRESETS.get(game.lower(), GAME_PRESETS["red"])
    _triggerbot_active = True

    # Kütüphane varlığını kontrol et
    try:
        import cv2
        import numpy as np
        use_cv2 = True
    except ImportError:
        use_cv2 = False

    try:
        import mss as _mss_mod
        use_mss = True
    except ImportError:
        use_mss = False

    # ── Paylaşılan durum sözlüğü (loop ↔ HUD thread) ────────────────────────
    state = {"detected": False, "shots": 0, "fps": 0, "pixels": 0}

    # ── Canlı HUD Overlay ────────────────────────────────────────────────────
    def run_hud():
        try:
            hud = tk.Tk()
            hud.overrideredirect(True)
            hud.attributes("-topmost", True)
            hud.attributes("-alpha", 0.92)
            hud.config(bg="#080808")

            sw = hud.winfo_screenwidth()
            hud.geometry(f"200x105+{sw - 215}+12")  # Sağ üst köşe

            tk.Label(
                hud, text="◈  TRİGGERBOT v2  ◈",
                font=("Consolas", 9, "bold"),
                fg="#00ff88", bg="#080808"
            ).pack(pady=(6, 1))

            lbl_status = tk.Label(
                hud, text="🟢  TARAMA",
                font=("Consolas", 12, "bold"),
                fg="#00ff88", bg="#080808"
            )
            lbl_status.pack()

            lbl_info = tk.Label(
                hud, text="Atış: 0   FPS: ---",
                font=("Consolas", 8),
                fg="#555555", bg="#080808"
            )
            lbl_info.pack(pady=(1, 0))

            lbl_pixels = tk.Label(
                hud, text="Piksel: 0",
                font=("Consolas", 8),
                fg="#333333", bg="#080808"
            )
            lbl_pixels.pack()

            def refresh():
                if not _triggerbot_active:
                    hud.destroy()
                    return
                if state["detected"]:
                    lbl_status.config(text="🔴  HEDEF!", fg="#ff2222")
                else:
                    lbl_status.config(text="🟢  TARAMA", fg="#00ff88")
                lbl_info.config(
                    text=f"Atış: {state['shots']}   FPS: {state['fps']}"
                )
                lbl_pixels.config(
                    text=f"Eşleşen piksel: {state['pixels']}"
                )
                hud.after(50, refresh)  # 20 Hz UI

            hud.after(50, refresh)
            hud.mainloop()
        except Exception:
            pass

    threading.Thread(target=run_hud, daemon=True).start()

    # ── Ana Tarama Döngüsü ───────────────────────────────────────────────────
    def loop():
        global _triggerbot_active
        import ctypes

        # DPI uyumluluğu — zaten ayarlıysa hata yakalanır, sorun yok
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        screen_w, screen_h = pyautogui.size()
        cx, cy = screen_w // 2, screen_h // 2

        if full_screen:
            monitor = {"top": 0, "left": 0, "width": screen_w, "height": screen_h}
        else:
            half = scan_zone
            x1 = max(0, cx - half)
            y1 = max(0, cy - half)
            x2 = min(screen_w, cx + half)
            y2 = min(screen_h, cy + half)
            monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}

        last_fire  = 0.0
        end_time   = time.time() + duration
        frame_time = time.time()
        fps_count  = 0

        if use_mss and use_cv2:
            # ── YÜKSEK PERFORMANS: mss + cv2 ─────────────────────────────────
            import mss
            import numpy as np
            import cv2

            with mss.mss() as sct:
                while _triggerbot_active and time.time() < end_time:
                    try:
                        # mss BGRA döndürür — Alpha kanalı at → BGR
                        raw = sct.grab(monitor)
                        frame = np.frombuffer(raw.raw, dtype=np.uint8)
                        frame = frame.reshape((raw.height, raw.width, 4))[:, :, :3]

                        found, pixel_count = _detect_color_cv2(frame, preset)
                        state["detected"] = found
                        state["pixels"]   = pixel_count

                        now = time.time()
                        if found and (now - last_fire) > cooldown:
                            if fire_delay > 0:
                                time.sleep(fire_delay)
                            _fast_left_click()
                            last_fire = time.time()
                            state["shots"] += 1

                        fps_count += 1
                        if now - frame_time >= 1.0:
                            state["fps"] = fps_count
                            fps_count  = 0
                            frame_time = now

                    except Exception:
                        pass
                    # sleep YOK — mss zaten doğal hız sınırı koyar
        else:
            # ── YEDEK: PIL ImageGrab ─────────────────────────────────────────
            from PIL import ImageGrab
            import numpy as np

            bbox = (
                monitor["left"],
                monitor["top"],
                monitor["left"] + monitor["width"],
                monitor["top"]  + monitor["height"],
            )
            while _triggerbot_active and time.time() < end_time:
                try:
                    img = ImageGrab.grab(bbox=bbox)
                    arr = np.array(img, dtype=np.uint8)
                    found = _detect_color_numpy(arr, preset)
                    state["detected"] = found
                    state["pixels"]   = 0

                    now = time.time()
                    if found and (now - last_fire) > cooldown:
                        if fire_delay > 0:
                            time.sleep(fire_delay)
                        _fast_left_click()
                        last_fire = time.time()
                        state["shots"] += 1

                    fps_count += 1
                    if now - frame_time >= 1.0:
                        state["fps"] = fps_count
                        fps_count  = 0
                        frame_time = now

                except Exception:
                    pass
                time.sleep(0.008)

        state["detected"] = False
        _triggerbot_active = False

    threading.Thread(target=loop, daemon=True).start()

    engine_desc = "mss + cv2 HSV + ctypes" if (use_mss and use_cv2) else "PIL fallback (pip install mss opencv-python)"
    scan_desc   = "TAM EKRAN" if full_screen else f"merkez ±{scan_zone}px ({scan_zone*2}x{scan_zone*2}px)"
    return (
        f"🎯 PRO Triggerbot v2 Aktif!\n"
        f"   • Oyun önayarı : {game.upper()}\n"
        f"   • Tarama alanı : {scan_desc}\n"
        f"   • Motor        : {engine_desc}\n"
        f"   • Tepki süresi : {int(fire_delay*1000)}ms\n"
        f"   • Soğuma       : {int(cooldown*1000)}ms\n"
        f"   • Süre         : {duration}s\n"
        f"   📺 Sağ üst köşede canlı HUD açıldı (piksel sayacı dahil)\n"
        f"   ⚠️  Durdurmak için tekrar 'triggerbot' komutunu ver."
    )

def anti_afk_bot(duration_minutes: float = 10.0) -> str:
    """
    Belirli aralıklarla rastgele W, A, S, D tuşlarına basarak ve zıplayarak
    oyunda AFK kalıp sunucudan atılmayı (kicklenmeyi) önler.
    """
    import random
    def loop():
        end_time = time.time() + (duration_minutes * 60)
        keys = ['w', 'a', 's', 'd', 'space']
        while time.time() < end_time:
            key = random.choice(keys)
            if key == 'space':
                pyautogui.press('space')
            else:
                pyautogui.keyDown(key)
                time.sleep(random.uniform(0.1, 0.4))
                pyautogui.keyUp(key)
                
            # Fareyi hafifçe hareket ettir
            pyautogui.moveRel(random.randint(-30, 30), random.randint(-30, 30), duration=0.2)
            time.sleep(random.uniform(4.0, 10.0))
            
    thread = threading.Thread(target=loop)
    thread.daemon = True
    thread.start()
    return f"🤖 Anti-AFK Botu {duration_minutes} dakika boyunca aktif! Sunucudan atılmanı önleyecek."

# ── 1. AIM ASSIST (RENK MERKEZİ TAKIP) ──────────────────────────────────────

_aimbot_active = False

def _find_color_centroid(frame_bgr, preset: dict):
    """
    Tespit edilen renk piksellerinin ağırlık merkezini (centroid) döndürür.
    Döndürür: (cx, cy) veya None
    """
    try:
        import cv2
        import numpy as np
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[:,:,0], hsv[:,:,1], hsv[:,:,2]
        sv_mask = (s >= preset["s_min"]) & (v >= preset["v_min"])
        h_mask  = np.zeros(h.shape, dtype=bool)
        for h_lo, h_hi in preset["h_ranges"]:
            h_mask |= (h >= h_lo) & (h <= h_hi)
        mask = (sv_mask & h_mask).astype(np.uint8) * 255
        # Gürültü temizle
        mask = cv2.erode(mask,  None, iterations=1)
        mask = cv2.dilate(mask, None, iterations=2)
        # En büyük kontur
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            return None
        c = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(c) < preset["pixel_threshold"]:
            return None
        M = cv2.moments(c)
        if M["m00"] == 0:
            return None
        return int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
    except Exception:
        return None


def aim_assist(
    duration: float = 60.0,
    game: str = "red",
    scan_zone: int = 300,
    smooth: float = 0.3,
    fov: int = 150,
) -> str:
    """
    Aim Assist — düşman rengi tespit edildiğinde fareyi hedefe doğru KAYDIRIR.
    Tam snap değil; smooth parametresi ile kademeli hareket eder.

    smooth=0.1 → çok hassas & hızlı snap
    smooth=0.5 → yavaş ve doğal kayma
    fov       → kaç piksel içindeki hedeflere tepki verilsin (merkezden uzaklık)
    """
    global _aimbot_active
    if _aimbot_active:
        _aimbot_active = False
        return "⛔ Aim Assist durduruldu."

    try:
        import cv2
        import numpy as np
        import mss
        import ctypes
    except ImportError as e:
        return f"❌ Gerekli kütüphane eksik: {e}. pip install mss opencv-python"

    preset = GAME_PRESETS.get(game.lower(), GAME_PRESETS["red"])
    _aimbot_active = True

    state = {"fps": 0, "locked": False}

    def run_hud():
        try:
            hud = tk.Tk()
            hud.overrideredirect(True)
            hud.attributes("-topmost", True)
            hud.attributes("-alpha", 0.88)
            hud.config(bg="#080808")
            sw = hud.winfo_screenwidth()
            hud.geometry(f"190x75+{sw - 205}+130")
            tk.Label(hud, text="◈  AIM ASSIST  ◈", font=("Consolas", 9, "bold"),
                     fg="#ffaa00", bg="#080808").pack(pady=(5,1))
            lbl = tk.Label(hud, text="🟡  TARAMA", font=("Consolas", 11, "bold"),
                           fg="#ffaa00", bg="#080808")
            lbl.pack()
            lbl_fps = tk.Label(hud, text="FPS: ---", font=("Consolas", 8),
                               fg="#444444", bg="#080808")
            lbl_fps.pack()
            def refresh():
                if not _aimbot_active:
                    hud.destroy(); return
                if state["locked"]:
                    lbl.config(text="🔶  KİLİTLENDİ!", fg="#ff8800")
                else:
                    lbl.config(text="🟡  TARAMA", fg="#ffaa00")
                lbl_fps.config(text=f"FPS: {state['fps']}")
                hud.after(50, refresh)
            hud.after(50, refresh)
            hud.mainloop()
        except Exception:
            pass

    threading.Thread(target=run_hud, daemon=True).start()

    def loop():
        global _aimbot_active
        screen_w, screen_h = pyautogui.size()
        cx, cy = screen_w // 2, screen_h // 2
        half = scan_zone
        monitor = {
            "top":    max(0, cy - half),
            "left":   max(0, cx - half),
            "width":  min(screen_w, cx + half) - max(0, cx - half),
            "height": min(screen_h, cy + half) - max(0, cy - half),
        }
        end_time   = time.time() + duration
        frame_time = time.time()
        fps_count  = 0

        with mss.mss() as sct:
            while _aimbot_active and time.time() < end_time:
                try:
                    raw   = sct.grab(monitor)
                    frame = np.frombuffer(raw.raw, dtype=np.uint8)
                    frame = frame.reshape((raw.height, raw.width, 4))[:,:,:3]

                    pt = _find_color_centroid(frame, preset)
                    if pt:
                        # Hedef ekran koordinatlarına çevir
                        tx = monitor["left"] + pt[0]
                        ty = monitor["top"]  + pt[1]
                        dx = tx - cx
                        dy = ty - cy
                        dist = (dx**2 + dy**2) ** 0.5

                        if dist < fov:
                            state["locked"] = True
                            # Smooth hareket: mevcut pozisyondan hedefe adım adım git
                            move_x = int(dx * smooth)
                            move_y = int(dy * smooth)
                            if abs(move_x) > 0 or abs(move_y) > 0:
                                ctypes.windll.user32.mouse_event(
                                    0x0001,         # MOUSEEVENTF_MOVE
                                    ctypes.c_long(move_x),
                                    ctypes.c_long(move_y),
                                    0, 0
                                )
                        else:
                            state["locked"] = False
                    else:
                        state["locked"] = False

                    fps_count += 1
                    now = time.time()
                    if now - frame_time >= 1.0:
                        state["fps"] = fps_count
                        fps_count  = 0
                        frame_time = now
                except Exception:
                    pass

        _aimbot_active = False

    threading.Thread(target=loop, daemon=True).start()
    return (
        f"🎯 Aim Assist Aktif!\n"
        f"   • Oyun  : {game.upper()}\n"
        f"   • FOV   : ±{fov}px (bu mesafe içindeki hedefler kilitlenir)\n"
        f"   • Smooth: {smooth} (düşük=hızlı snap, yüksek=yumuşak)\n"
        f"   • Süre  : {duration}s\n"
        f"   ⚠️  Durdurmak için tekrar 'aim assist' komutunu ver."
    )


# ── 2. ANTİ-RECOİL (GERİ TEPME BASTIRMA) ────────────────────────────────────

_recoil_active = False

def recoil_control(
    recoil_y: int = 5,
    recoil_x: int = 0,
    duration: float = 60.0,
    fire_key: str  = "mouse1",
) -> str:
    """
    Anti-Recoil — sol tık basılı tutulduğu her frame'de fareyi aşağı kaydırarak
    geri tepmeyi dengeler.

    recoil_y  → her frame'de aşağı kayma miktarı (piksel). CS2 için 3-6 önerilir.
    recoil_x  → yatay kayma (çoğu oyunda 0)
    fire_key  → izlenecek tuş ('mouse1'=sol tık diğer tuşlar için: 'mouse2','f' vb.)
    """
    global _recoil_active
    if _recoil_active:
        _recoil_active = False
        return "⛔ Anti-Recoil durduruldu."

    try:
        import ctypes
    except ImportError:
        return "❌ ctypes modülü bulunamadı."

    _recoil_active = True

    def loop():
        global _recoil_active
        VK_LBUTTON = 0x01
        VK_RBUTTON = 0x02
        key_map = {"mouse1": VK_LBUTTON, "mouse2": VK_RBUTTON}
        vk = key_map.get(fire_key.lower(), VK_LBUTTON)

        end_time = time.time() + duration
        while _recoil_active and time.time() < end_time:
            # GetAsyncKeyState: tuş basılı mı?
            state = ctypes.windll.user32.GetAsyncKeyState(vk)
            if state & 0x8000:
                # Ateş ediliyor — geri tepmeyi dengele
                ctypes.windll.user32.mouse_event(
                    0x0001,                      # MOUSEEVENTF_MOVE
                    ctypes.c_long(recoil_x),
                    ctypes.c_long(recoil_y),
                    0, 0
                )
            time.sleep(0.008)  # ~125 Hz polling

        _recoil_active = False

    threading.Thread(target=loop, daemon=True).start()
    return (
        f"🎮 Anti-Recoil Aktif!\n"
        f"   • Dikey dengeleme  : {recoil_y}px/frame\n"
        f"   • Yatay dengeleme  : {recoil_x}px/frame\n"
        f"   • Süre             : {duration}s\n"
        f"   ⚠️  Durdurmak için tekrar 'anti recoil' komutunu ver."
    )


# ── 3. RAPID FIRE (HIZLI ATEŞ) ───────────────────────────────────────────────

_rapidfire_active = False

def rapid_fire(cps: int = 15, duration: float = 30.0) -> str:
    """
    Rapid Fire — sol tık basılı tutulduğunda, oyunun kendi orijinal ateş hızını
    aşacak şekilde mouseDown/mouseUp döngüsü çalıştırır.
    Yarı otomatik silahlar (Deagle, Tec-9 vb.) için idealdir.

    cps → saniyedeki tıklama (clicks per second). 15-25 arası önerilir.
    """
    global _rapidfire_active
    if _rapidfire_active:
        _rapidfire_active = False
        return "⛔ Rapid Fire durduruldu."

    try:
        import ctypes
    except ImportError:
        return "❌ ctypes bulunamadı."

    _rapidfire_active = True
    delay = 1.0 / max(1, cps)

    def loop():
        global _rapidfire_active
        VK_LBUTTON = 0x01
        end_time = time.time() + duration
        while _rapidfire_active and time.time() < end_time:
            if ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON) & 0x8000:
                ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)  # UP
                time.sleep(delay / 2)
                ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)  # DOWN
                time.sleep(delay / 2)
            else:
                time.sleep(0.005)
        _rapidfire_active = False

    threading.Thread(target=loop, daemon=True).start()
    return (
        f"⚡ Rapid Fire Aktif! ({cps} tık/sn)\n"
        f"   Sol tık basılı tuttuğunda otomatik olarak {cps}x/sn ateş eder.\n"
        f"   ⚠️  Durdurmak için tekrar 'rapid fire' komutunu ver."
    )


# ── 4. BUNNY HOP (OTOMATİK ZIPLAMA) ─────────────────────────────────────────

_bhop_active = False

def bunny_hop(duration: float = 30.0, jump_key: str = "space") -> str:
    """
    Bunny Hop — zıplama tuşuna tam zamanında basarak sürekli bhop yapmayı sağlar.
    Kullanıcı zıplama tuşunu basılı tuttuğunda otomatik olarak zamanlanır.
    """
    global _bhop_active
    if _bhop_active:
        _bhop_active = False
        return "⛔ Bunny Hop durduruldu."

    try:
        import ctypes
    except ImportError:
        return "❌ ctypes bulunamadı."

    _bhop_active = True

    VK_MAP = {
        "space": 0x20, "ctrl": 0x11, "shift": 0xA0,
        "e": 0x45, "q": 0x51, "f": 0x46,
    }
    vk = VK_MAP.get(jump_key.lower(), 0x20)

    def loop():
        global _bhop_active
        end_time = time.time() + duration
        was_pressed = False
        while _bhop_active and time.time() < end_time:
            pressed = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
            if pressed and not was_pressed:
                # Tuşa yeni basıldı — hemen bırak ve kısa aralıklarla tekrar bas
                pyautogui.keyUp(jump_key)
                time.sleep(0.013)
                pyautogui.keyDown(jump_key)
                time.sleep(0.013)
                pyautogui.keyUp(jump_key)
            was_pressed = pressed
            time.sleep(0.007)
        _bhop_active = False

    threading.Thread(target=loop, daemon=True).start()
    return (
        f"🐇 Bunny Hop Aktif! (tuş: {jump_key.upper()})\n"
        f"   Zıplama tuşunu basılı tut — otomatik zamanlanır.\n"
        f"   ⚠️  Durdurmak için tekrar 'bhop' komutunu ver."
    )


# ── 5. RENK KALİBRATÖRÜ (EKRAN MERKEZİNDEN ÖRNEKLEME) ──────────────────────

def color_calibrate(sample_radius: int = 5) -> str:
    """
    Ekranın tam ortasından renk örneği alır ve otomatik HSV önayarı oluşturur.
    Kullanım: Nişanını düşmanın üzerine getir ve 'renk kalibre et' de.
    """
    try:
        import mss
        import numpy as np
        import cv2
    except ImportError:
        return "❌ mss veya opencv-python kurulu değil."

    screen_w, screen_h = pyautogui.size()
    cx, cy = screen_w // 2, screen_h // 2
    r = sample_radius

    monitor = {
        "top":    max(0, cy - r),
        "left":   max(0, cx - r),
        "width":  r * 2 + 1,
        "height": r * 2 + 1,
    }

    with mss.mss() as sct:
        raw   = sct.grab(monitor)
        frame = np.frombuffer(raw.raw, dtype=np.uint8)
        frame = frame.reshape((raw.height, raw.width, 4))[:,:,:3]

    hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    h_med = int(np.median(hsv[:,:,0]))
    s_med = int(np.median(hsv[:,:,1]))
    v_med = int(np.median(hsv[:,:,2]))

    # Tolerans
    h_lo = max(0,   h_med - 12)
    h_hi = min(179, h_med + 12)
    s_lo = max(0,   s_med - 40)
    v_lo = max(0,   v_med - 40)

    # Ortalama BGR → RGB
    avg_bgr = frame.mean(axis=(0,1)).astype(int)
    avg_rgb = (int(avg_bgr[2]), int(avg_bgr[1]), int(avg_bgr[0]))

    # GAME_PRESETS'e "custom" olarak ekle
    GAME_PRESETS["custom"] = {
        "h_ranges": [(h_lo, h_hi)],
        "s_min": s_lo,
        "v_min": v_lo,
        "pixel_threshold": 4,
    }

    return (
        f"🎨 Renk Kalibrasyonu Tamamlandı!\n"
        f"   Ortalama renk (RGB) : {avg_rgb}\n"
        f"   HSV median          : H={h_med}, S={s_med}, V={v_med}\n"
        f"   Oluşturulan aralık  : H=[{h_lo}-{h_hi}], S≥{s_lo}, V≥{v_lo}\n"
        f"   Önayar adı          : 'custom'\n"
        f"   Kullanım            : triggerbot game=custom\n"
        f"                         aim assist game=custom"
    )


# ── 6. STEAM OYUN LİSTESİ ────────────────────────────────────────────────────

def list_installed_steam_games() -> str:
    """Sistemde yüklü tüm Steam oyunlarını listeler."""
    games = get_installed_steam_games()
    if not games:
        return "❌ Hiç Steam oyunu bulunamadı veya Steam kurulu değil."
    lines = [f"🎮 Yüklü Steam Oyunları ({len(games)} adet):"]
    for i, (name, appid) in enumerate(sorted(games.items()), 1):
        lines.append(f"   {i:>3}. {name.title():<35} [AppID: {appid}]")
    return "\n".join(lines)


# ── MERKEZİ KONTROL ──────────────────────────────────────────────────────────

def game_helper_control(action: str, **kwargs) -> str:
    """Oyun asistanı merkezi yönetim fonksiyonu."""
    if action == "launch_game":
        game_name = kwargs.get("game_name", "")
        if not game_name:
            return "Hata: Oyun adı belirtilmedi."
        return launch_steam_game(game_name)

    elif action == "list_games":
        return list_installed_steam_games()

    elif action == "auto_click":
        cps = int(kwargs.get("cps", 10))
        duration = int(kwargs.get("duration", 5))
        return auto_clicker(cps, duration)

    elif action == "hold_click":
        button = kwargs.get("button", "left")
        duration = float(kwargs.get("duration", 3.0))
        return hold_click(button, duration)

    elif action == "hold_key":
        key = kwargs.get("key", "")
        if not key:
            return "Hata: Basılı tutulacak tuş belirtilmedi."
        duration = float(kwargs.get("duration", 3.0))
        return hold_key(key, duration)

    elif action == "press_sequence":
        seq = kwargs.get("sequence", "")
        if not seq:
            return "Hata: Tuş dizisi belirtilmedi."
        delay = float(kwargs.get("delay", 0.5))
        return press_keys_sequence(seq, delay)

    elif action == "toggle_crosshair":
        color = kwargs.get("color", "red")
        size  = int(kwargs.get("size", 12))
        style = kwargs.get("style", "dot")
        return toggle_crosshair(color, size, style)

    elif action == "boost_game":
        proc_name = kwargs.get("game_name", "")
        if not proc_name:
            return "Hata: Güçlendirilecek oyunun işlem adı belirtilmedi."
        return boost_game_performance(proc_name)

    elif action == "restore_priorities":
        return restore_priorities()

    elif action == "triggerbot":
        duration    = float(kwargs.get("duration",    60.0))
        scan_zone   = int(kwargs.get("scan_zone",     400))
        game        = str(kwargs.get("game", kwargs.get("enemy_color", "red")))
        fire_delay  = float(kwargs.get("fire_delay",  0.03))
        cooldown    = float(kwargs.get("cooldown",    0.08))
        full_screen = bool(kwargs.get("full_screen",  False))
        return triggerbot_color_change(duration, scan_zone, game, fire_delay, cooldown, full_screen)

    elif action == "aim_assist":
        duration  = float(kwargs.get("duration",  60.0))
        game      = str(kwargs.get("game",        "red"))
        scan_zone = int(kwargs.get("scan_zone",   300))
        smooth    = float(kwargs.get("smooth",    0.3))
        fov       = int(kwargs.get("fov",         150))
        return aim_assist(duration, game, scan_zone, smooth, fov)

    elif action == "recoil_control":
        recoil_y  = int(kwargs.get("recoil_y",   5))
        recoil_x  = int(kwargs.get("recoil_x",   0))
        duration  = float(kwargs.get("duration",  60.0))
        fire_key  = str(kwargs.get("fire_key",    "mouse1"))
        return recoil_control(recoil_y, recoil_x, duration, fire_key)

    elif action == "rapid_fire":
        cps      = int(kwargs.get("cps",      15))
        duration = float(kwargs.get("duration", 30.0))
        return rapid_fire(cps, duration)

    elif action == "bunny_hop":
        duration  = float(kwargs.get("duration",  30.0))
        jump_key  = str(kwargs.get("jump_key",    "space"))
        return bunny_hop(duration, jump_key)

    elif action == "color_calibrate":
        radius = int(kwargs.get("radius", 5))
        return color_calibrate(radius)

    elif action == "anti_afk":
        duration_minutes = float(kwargs.get("duration", 10.0))
        return anti_afk_bot(duration_minutes)

    return f"Bilinmeyen oyun aksiyonu: {action}"

