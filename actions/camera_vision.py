# Alp Ünlü tarafından yapılmıştır — @alppunlu
from __future__ import annotations

import io
import time
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from google import genai
from google.genai import types

from app_config import get_app_config_value

def capture_webcam_image() -> tuple[bool, str, Path | None]:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return False, "Kameraya erişilemedi veya takılı bir kamera bulunamadı.", None
    
    # Isınması için birkaç frame atla
    for _ in range(5):
        cap.read()
        time.sleep(0.1)

    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        return False, "Kameradan görüntü alınamadı.", None
        
    handle = tempfile.NamedTemporaryFile(prefix="jarvis-camera-", suffix=".jpg", delete=False)
    image_path = Path(handle.name)
    handle.close()
    
    success = cv2.imwrite(str(image_path), frame)
    if not success:
        return False, "Kamera görüntüsü diske kaydedilemedi.", None
        
    return True, "", image_path

def _vision_prompt(query: str) -> str:
    user_query = (query or "Önünde ne görüyorsun?").strip()
    return (
        "Sen F.R.I.D.A.Y için çalışan, bilgisayar kamerası aracılığıyla dış dünyayı gören gelişmiş bir yapay zekasın.\n"
        "Aşağıdaki görüntü bilgisayar kamerasından yeni çekildi.\n\n"
        "Görevlerin ve Yeteneklerin:\n"
        "1. Genel Tanımlama: Kullanıcı sana bir şey gösteriyorsa, ne olduğunu, nerede olduğunu detaylıca açıkla.\n"
        "2. Soru Cevaplama: Kullanıcının sorduğu soruyu doğrudan bu görüntüye bakarak cevapla.\n"
        "3. Uzunluk, Alan ve Hacim Tahmini: Kullanıcı boyut, uzunluk, alan veya hacim sorarsa, görüntüdeki standart veya bilinen nesneleri (eller, yüzler, klavye vb.) referans alarak matematiksel bir tahmin yap. Kesin olamasan bile elinden gelen en mantıklı tahmini santimetre (cm) veya metre (m) cinsinden belirt.\n"
        "4. Su Terazisi (Eğim Analizi): Kullanıcı bir cismin düz olup olmadığını sorarsa, görüntüdeki düz çizgileri (masa kenarı, duvar, ufuk çizgisi) referans alarak nesnenin eğimini analiz et. Sağa veya sola yatık olup olmadığını belirt.\n"
        "5. Plaka Okuma (OCR): Görüntüde bir araba plakası varsa, üzerindeki harf ve rakamları eksiksiz bir şekilde oku ve metin olarak açıkça belirt.\n"
        "6. Uydurma yapma. Kamerada net görünmeyen bir şeyse dürüstçe söyle.\n\n"
        f"Kullanıcı sorusu: {user_query}\n\n"
        "Yanıtı Türkçe, net, analitik ve akıcı bir asistan tonuyla ver. "
        "Kullanıcının sorduğu spesifik detayı (plaka, boyut, eğim) mutlaka net bir şekilde belirt."
    )

def _build_image_part(image_path: Path) -> types.Part:
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            work = img.convert("RGB")
            max_dim = 1000
            if max(work.size) > max_dim:
                work.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            jpg_buffer = io.BytesIO()
            work.save(jpg_buffer, format="JPEG", quality=85, optimize=True)
            return types.Part.from_bytes(data=jpg_buffer.getvalue(), mime_type="image/jpeg")
    except Exception:
        return types.Part.from_bytes(
            data=image_path.read_bytes(),
            mime_type="image/jpeg",
        )

def analyze_camera(query: str) -> str:
    ok, error_msg, image_path = capture_webcam_image()
    if not ok or not image_path:
        return error_msg
        
    try:
        api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
        if not api_key:
            return "Gemini API anahtarı eksik olduğu için kamera analizi yapılamadı."

        prompt = _vision_prompt(query)
        client = genai.Client(api_key=api_key)
        image_part = _build_image_part(image_path)
        
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[
                types.Part.from_text(text=prompt),
                image_part,
            ],
            config=types.GenerateContentConfig(
                temperature=0.3,
            ),
        )
        
        text = str(getattr(response, "text", "") or "").strip()
        if not text:
            # Fallback
            candidates = getattr(response, "candidates", None) or []
            for candidate in candidates:
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    pt = str(getattr(part, "text", "") or "").strip()
                    if pt:
                        text += pt + "\n"
                        
        if text:
            return f"[Kamera Görüntüsü] {text.strip()}"
        return "Kamera görüntüsü analiz edilemedi."
        
    except Exception as exc:
        return f"Kamera analizi başarısız oldu: {exc}"
    finally:
        try:
            if image_path and image_path.exists():
                image_path.unlink()
        except Exception:
            pass


# ── Sentinel & Gesture Background Threads ─────────────────────────────────────
import threading
import pyautogui
from actions.sys_control import set_volume, get_volume

_sentinel_thread = None
_sentinel_stop_event = threading.Event()
_sentinel_lock = threading.Lock()

_gesture_thread = None
_gesture_stop_event = threading.Event()
_gesture_lock = threading.Lock()

# Thread-safe frame caching for WiFi Mobil HUD
_latest_frame_lock = threading.Lock()
_latest_frame = None


def is_sentinel_active() -> bool:
    with _sentinel_lock:
        return _sentinel_thread is not None and _sentinel_thread.is_alive()


def is_gesture_active() -> bool:
    with _gesture_lock:
        return _gesture_thread is not None and _gesture_thread.is_alive()


def get_latest_frame():
    with _latest_frame_lock:
        return _latest_frame


def _sentinel_worker(stop_event, ui, phone_number):
    import cv2
    import time
    from pathlib import Path
    from actions.whatsapp import send_whatsapp_message
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[SENTINEL] Kamera acilamadi.")
        return
        
    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return
        
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (21, 21), 0)
    
    last_alert_time = 0.0
    print("[SENTINEL] Nobetci Modu aktif, odadaki hareketler izleniyor...")
    
    workspace_dir = Path("c:/Users/samet/OneDrive/Masaüstü/jarvis")
    captures_dir = workspace_dir / "security_captures"
    captures_dir.mkdir(parents=True, exist_ok=True)
    
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.5)
            continue
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        frame_delta = cv2.absdiff(prev_gray, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) < 9000:
                continue
            motion_detected = True
            # Draw bounding box for visual feed
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            
        # Update cache for WiFi HUD
        with _latest_frame_lock:
            global _latest_frame
            _latest_frame = frame.copy()
            
        if motion_detected:
            curr_time = time.time()
            if curr_time - last_alert_time > 15.0:
                last_alert_time = curr_time
                print("[SENTINEL] UYARI: Odada hareket tespit edildi!")
                
                # Gemini AI Yüz Tanıma Koruması
                profile_path = workspace_dir / "profile.jpg"
                if profile_path.exists():
                    print("[SENTINEL] Yetkili profil tespiti için Gemini AI analizi başlatılıyor...")
                    temp_intruder_path = workspace_dir / "temp_intruder.jpg"
                    cv2.imwrite(str(temp_intruder_path), frame)
                    
                    try:
                        from google import genai
                        from google.genai import types
                        from app_config import get_app_config_value
                        
                        api_key = get_app_config_value("gemini_api_key")
                        if api_key:
                            client = genai.Client(api_key=api_key)
                            with open(str(profile_path), "rb") as f:
                                ref_bytes = f.read()
                            with open(str(temp_intruder_path), "rb") as f:
                                int_bytes = f.read()
                                
                            ref_part = types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
                            int_part = types.Part.from_bytes(data=int_bytes, mime_type="image/jpeg")
                            
                            response = client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=[
                                    ref_part,
                                    int_part,
                                    "Birinci resim yetkili kullanıcı Samet'e aittir. İkinci resim odadaki hareket anında çekilmiştir.\n"
                                    "İkinci resimdeki kişinin (yüz hatları, saç şekli, genel görünüş) birinci resimdeki Samet ile aynı kişi olup olmadığını analiz et.\n"
                                    "Eğer resimde sadece bir el, kol veya nesne varsa ve yüz net görünmüyorsa, bunu şüpheli hareket kabul et ve 'YABANCI' döndür.\n"
                                    "Eğer resimdeki kişi Samet ise veya ikinci resimde kimse yoksa sadece 'SAMET' kelimesini döndür.\n"
                                    "Eğer resimdeki kişi kesinlikle Samet değilse (başka biri, yabancıysa), sadece 'YABANCI' kelimesini döndür.\n"
                                    "Cevabında sadece ve sadece 'SAMET' veya 'YABANCI' yaz, başka hiçbir açıklama ekleme."
                                ]
                            )
                            answer = str(response.text).strip().upper()
                            print(f"[SENTINEL] Gemini AI Analiz Sonucu: {answer}")
                            
                            if temp_intruder_path.exists():
                                try:
                                    os.remove(temp_intruder_path)
                                except Exception:
                                    pass
                                    
                            if "SAMET" in answer:
                                print("[SENTINEL] Yetkili kullanıcı (Samet) tespit edildi. Alarm İPTAL edildi.")
                                if ui:
                                    ui.write_log("SYS: Samet Bey algılandı. Sentinel alarmı iptal edildi.")
                                prev_gray = gray
                                continue
                            else:
                                print("[SENTINEL] YABANCI tespit edildi! Güvenlik ihlali tetikleniyor...")
                        else:
                            print("[SENTINEL] API anahtarı bulunamadı, varsayılan alarm tetikleniyor.")
                    except Exception as ex:
                        print(f"[SENTINEL] AI Yüz tanıma hatası, varsayılan alarm tetikleniyor: {ex}")
                        if temp_intruder_path.exists():
                            try:
                                    os.remove(temp_intruder_path)
                            except Exception:
                                    pass
                
                # Alarm sesini çal
                if ui and hasattr(ui, "sound") and ui.sound:
                    ui.sound.play_error()
                    
                # Snap çek ve kaydet
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"intruder_{timestamp}.jpg"
                filepath = captures_dir / filename
                cv2.imwrite(str(filepath), frame)
                
                alert_text = "UYARI: Odada hareket tespit edildi!"
                
                if phone_number:
                    try:
                        # 1. Sohbeti aç ve mesajı yaz
                        send_whatsapp_message(message=alert_text, phone_number=phone_number, send_now=True)
                        
                        # 2. Resmi panoya kopyala (Windows için PowerShell)
                        import subprocess
                        ps_cmd = f'Add-Type -AssemblyName System.Windows.Forms; $img = [System.Drawing.Image]::FromFile("{str(filepath)}"); [System.Windows.Forms.Clipboard]::SetImage($img)'
                        subprocess.run(["powershell", "-Command", ps_cmd], check=True)
                        
                        # 3. WhatsApp'ın açılmasını bekle (Yavaş yüklemeler için 5 sn)
                        time.sleep(5)
                        
                        # 4. Resmi yapıştır ve gönder
                        import pyautogui
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(1)
                        pyautogui.press('enter')
                        print("[SENTINEL] Fotoğraf başarıyla WhatsApp'tan gönderildi.")
                        
                    except Exception as e:
                        print(f"[SENTINEL] WhatsApp bildirimi veya fotoğraf gönderimi başarısız: {e}")
                        
                # Tek seferlik calisma: alarm calip resmi attiktan sonra modu otomatik kapat
                if ui:
                    ui.write_log("SYS: Sentinel hareket tespit etti, güvenlik çemberi kapatılıyor.")
                stop_event.set()
                        
        prev_gray = gray
        time.sleep(0.4)
        
    cap.release()
    print("[SENTINEL] Nobetci Modu kapatildi.")


def start_sentinel_mode(ui_instance=None, phone_number="905537711924") -> str:
    global _sentinel_thread, _sentinel_stop_event
    with _sentinel_lock:
        if _sentinel_thread and _sentinel_thread.is_alive():
            return "Nöbetçi Modu zaten aktif."
            
        _sentinel_stop_event.clear()
        _sentinel_thread = threading.Thread(
            target=_sentinel_worker,
            args=(_sentinel_stop_event, ui_instance, phone_number),
            daemon=True
        )
        _sentinel_thread.start()
        return "Nöbetçi Modu başarıyla aktifleştirildi. Odanız güvenlik çemberi altında."


def stop_sentinel_mode() -> str:
    global _sentinel_thread, _sentinel_stop_event
    with _sentinel_lock:
        if not _sentinel_thread or not _sentinel_thread.is_alive():
            return "Nöbetçi Modu zaten kapalı."
            
        _sentinel_stop_event.set()
        _sentinel_thread = None
        return "Nöbetçi Modu kapatıldı. Güvenlik çemberi dev dışı bırakıldı."


def _gesture_worker(stop_event, ui):
    import cv2
    import time
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[GESTURE] Kamera acilamadi.")
        return
        
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320) if hasattr(cv2, "CAP_PROP_FRAME_WIDTH") else None
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240) if hasattr(cv2, "CAP_PROP_FRAME_HEIGHT") else None
    
    fgbg = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=24, detectShadows=False)
    motion_history = []
    
    last_action_time = 0.0
    action_cooldown = 1.0
    print("[GESTURE] Jest Kontrolu aktif, el hareketleri izleniyor...")
    
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.03)
            continue
            
        frame = cv2.flip(frame, 1)
        fgmask = fgbg.apply(frame)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)
        fgmask = cv2.dilate(fgmask, kernel, iterations=2)
        
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        hand_found = False
        cx, cy = None, None
        
        if contours:
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)
            
            if area > 1200:
                hand_found = True
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    # Draw circle for visual feed
                    cv2.circle(frame, (cx, cy), 10, (0, 255, 0), -1)
                    
        curr_time = time.time()
        motion_history = [pt for pt in motion_history if curr_time - pt[2] < 0.6]
        
        if hand_found and cx is not None and cy is not None:
            motion_history.append((cx, cy, curr_time))
            
            if curr_time - last_action_time > action_cooldown:
                if len(motion_history) >= 8:
                    first_pt = motion_history[0]
                    last_pt = motion_history[-1]
                    
                    dx = last_pt[0] - first_pt[0]
                    dy = last_pt[1] - first_pt[1]
                    dt = last_pt[2] - first_pt[2]
                    
                    if dt > 0.15:
                        # 1. Hold Still -> Play/Pause
                        xs = [pt[0] for pt in motion_history]
                        ys = [pt[1] for pt in motion_history]
                        var_x = np.var(xs) if len(xs) > 0 else 999.0
                        var_y = np.var(ys) if len(ys) > 0 else 999.0
                        
                        if len(xs) >= 15 and var_x < 3.5 and var_y < 3.5 and dt > 0.7:
                            print("[GESTURE] ||| DURAKLAT / DEVAM ET (Hold Still)")
                            pyautogui.press('playpause')
                            last_action_time = curr_time
                            motion_history = []
                            continue
                            
                        # 2. Swipe Right -> Next
                        if abs(dx) > abs(dy) * 1.5 and abs(dx) > 65:
                            if dx > 0:
                                print("[GESTURE] >>> SONRAKI SARKI (Swipe Right)")
                                pyautogui.press('nexttrack')
                                last_action_time = curr_time
                                motion_history = []
                            else:
                                print("[GESTURE] <<< ONCEKI SARKI (Swipe Left)")
                                pyautogui.press('prevtrack')
                                last_action_time = curr_time
                                motion_history = []
                                
                        # 3. Swipe Up/Down -> Volume
                        elif abs(dy) > abs(dx) * 1.5 and abs(dy) > 55:
                            if dy < 0:
                                print("[GESTURE] ^^^ SES ARTIR (Swipe Up)")
                                current_vol = get_volume()
                                new_vol = min(100, current_vol + 10)
                                set_volume(new_vol)
                                last_action_time = curr_time
                                motion_history = []
                            else:
                                print("[GESTURE] vvv SES AZALT (Swipe Down)")
                                current_vol = get_volume()
                                new_vol = max(0, current_vol - 10)
                                set_volume(new_vol)
                                last_action_time = curr_time
                                motion_history = []
                                
        # Update cache for WiFi HUD
        with _latest_frame_lock:
            global _latest_frame
            _latest_frame = frame.copy()
            
        time.sleep(0.03)
        
    cap.release()
    print("[GESTURE] Jest Kontrolu kapatildi.")


def start_gesture_control(ui_instance=None) -> str:
    global _gesture_thread, _gesture_stop_event
    with _gesture_lock:
        if _gesture_thread and _gesture_thread.is_alive():
            return "Jestle Medya Kontrolü zaten aktif."
            
        _gesture_stop_event.clear()
        _gesture_thread = threading.Thread(
            target=_gesture_worker,
            args=(_gesture_stop_event, ui_instance),
            daemon=True
        )
        _gesture_thread.start()
        return "Jestle Medya Kontrolü başarıyla aktifleştirildi. El hareketleriniz izleniyor."


def stop_gesture_control() -> str:
    global _gesture_thread, _gesture_stop_event
    with _gesture_lock:
        if not _gesture_thread or not _gesture_thread.is_alive():
            return "Jestle Medya Kontrolü zaten kapalı."
            
        _gesture_stop_event.set()
        _gesture_thread = None
        return "Jestle Medya Kontrolü kapatıldı."


def register_face(ui_instance=None) -> str:
    import cv2
    import time
    from pathlib import Path
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Yüz kaydedilemedi: Kamera açılamadı."
        
    # Warm up camera
    for _ in range(5):
        cap.read()
        time.sleep(0.1)
        
    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        return "Yüz kaydedilemedi: Görüntü alınamadı."
        
    workspace_dir = Path("c:/Users/samet/OneDrive/Masaüstü/jarvis")
    filepath = workspace_dir / "profile.jpg"
    
    cv2.imwrite(str(filepath), frame)
    
    if ui_instance:
        ui_instance.write_log("SYS: Yüz profiliniz 'profile.jpg' olarak kaydedildi.")
        
    return "Yüz profiliniz başarıyla kaydedildi. Artık F.R.I.D.A.Y. sizi tanıyarak alarmı tetiklemeyecektir."
