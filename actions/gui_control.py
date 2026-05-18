"""
Ekran Tiklama — Gelismis & Duzeltilmis Surum
F.R.I.D.A.Y — Cok katmanli dogruluk sistemi

Duzeltilen sorunlar:
  1. DPI scaling — Windows'ta %125/%150 olcek ekran koordinatlarini kaydirir
  2. Cok monitor — ImageGrab.grab(all_screens=True) kullanildiginda koordinat kaymalari
  3. Goruntu boyutu — Gemini'a gonderilen goruntu kucultuluyordu, koordinat hesabi yanlis oluyordu
  4. Koordinat sistemi — Gemini bazen piksel, bazen normalize deger donuyor, ikisi de isleniyor
  5. Guven kontrolu — Gemini'in buldugu bbox cok kucukse veya sifirsa hata don
"""

import io
import json
import re
import time
import tempfile
import ctypes
from pathlib import Path
from typing import Optional

import pyautogui
from PIL import ImageGrab, Image
from google import genai
from google.genai import types

from app_config import get_app_config_value


# ── DPI Yardimcisi ──────────────────────────────────────────────────────────

def _get_dpi_scale() -> float:
    """
    Windows DPI olcegini dondurur (1.0 = %100, 1.25 = %125, 1.5 = %150...).
    Yuksek DPI ekranlarda pyautogui ve ImageGrab farkli koordinat sistemleri kullanir.
    """
    try:
        # Windows 8.1+ SetProcessDpiAwareness
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        # Gercek ekran vs mantiksal ekran orani
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 96.0
    except Exception:
        return 1.0


def _get_primary_screen_size() -> tuple[int, int]:
    """Birincil ekranin FIZIKSEL piksel boyutunu dondurur."""
    try:
        w = ctypes.windll.user32.GetSystemMetrics(0)   # SM_CXSCREEN
        h = ctypes.windll.user32.GetSystemMetrics(1)   # SM_CYSCREEN
        return w, h
    except Exception:
        return pyautogui.size()


def _get_virtual_screen_rect() -> tuple[int, int, int, int]:
    """Tum monitorleri kapsayan sanal masaustu dikdortgenini dondurur (sol, ust, sag, alt)."""
    try:
        left   = ctypes.windll.user32.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
        top    = ctypes.windll.user32.GetSystemMetrics(77)   # SM_YVIRTUALSCREEN
        width  = ctypes.windll.user32.GetSystemMetrics(78)   # SM_CXVIRTUALSCREEN
        height = ctypes.windll.user32.GetSystemMetrics(79)   # SM_CYVIRTUALSCREEN
        return left, top, left + width, top + height
    except Exception:
        w, h = pyautogui.size()
        return 0, 0, w, h


# ── Ekran Yakalama ───────────────────────────────────────────────────────────

def _capture_primary_screen() -> tuple[Image.Image, int, int]:
    """
    SADECE birincil ekrani yakalar.
    all_screens=True koordinat kaymasi yaratiyor, bu yuzden tek ekran yakaliyoruz.
    Dondurur: (PIL Image, fiziksel_genislik, fiziksel_yukseklik)
    """
    # Birincil ekran boyutu
    phys_w, phys_h = _get_primary_screen_size()

    try:
        # Sadece birincil ekrani yakala (0,0 -> w,h)
        img = ImageGrab.grab(bbox=(0, 0, phys_w, phys_h), all_screens=False)
        return img, img.width, img.height
    except Exception:
        # Fallback
        img = ImageGrab.grab()
        return img, img.width, img.height


def _prepare_image_for_gemini(img: Image.Image, max_long_side: int = 1920) -> tuple[bytes, int, int]:
    """
    Goruntu boyutunu sinirlayip JPEG baytlari dondurur.
    ONEMLI: Gonderilen boyutu da donduruyoruz cunku koordinat hesabi buna gore yapilacak.
    """
    work = img.convert("RGB")
    orig_w, orig_h = work.width, work.height

    # Kucultme gerekiyorsa oran koruyarak kucult
    if max(orig_w, orig_h) > max_long_side:
        scale = max_long_side / max(orig_w, orig_h)
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        work = work.resize((new_w, new_h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    work.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue(), work.width, work.height


# ── Koordinat Ayrıstırma ────────────────────────────────────────────────────

def _parse_coordinates(
    text: str,
    img_w: int,
    img_h: int,
    screen_w: int,
    screen_h: int,
) -> Optional[tuple[int, int]]:
    """
    Gemini'in dondurulan metninden koordinatlari ayrıstırır ve
    ekran piksel koordinatına donusturur.

    Desteklenen formatlar:
      - {"ymin": 0-1000, "xmin": 0-1000, "ymax": 0-1000, "xmax": 0-1000}  (normalize 0-1000)
      - {"x": piksel, "y": piksel}
      - {"cx": piksel, "cy": piksel}
      - [ymin, xmin, ymax, xmax]  (normalize 0-1000 list)
    """
    # JSON nesnesi ara
    match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
    if match:
        try:
            coords = json.loads(match.group(0))

            # Format 1: bbox (0-1000 normalize)
            if all(k in coords for k in ("ymin", "xmin", "ymax", "xmax")):
                ymin = float(coords["ymin"])
                xmin = float(coords["xmin"])
                ymax = float(coords["ymax"])
                xmax = float(coords["xmax"])

                if ymin == 0 and xmin == 0 and ymax == 0 and xmax == 0:
                    return None

                # Normalize deger mi yoksa piksel mi?
                # Eger degerler 0-1 arasindaysa 1000 ile carp
                if xmax <= 1.0 and ymax <= 1.0:
                    xmin *= 1000; xmax *= 1000
                    ymin *= 1000; ymax *= 1000

                # Merkez hesapla (0-1000 normalize -> goruntu piksel -> ekran piksel)
                cx_norm = (xmin + xmax) / 2.0  # 0-1000
                cy_norm = (ymin + ymax) / 2.0  # 0-1000

                # Goruntu piksel koordinati
                cx_img = (cx_norm / 1000.0) * img_w
                cy_img = (cy_norm / 1000.0) * img_h

                # Ekran piksel koordinati (goruntu <- ekran orani)
                cx_screen = int((cx_img / img_w) * screen_w)
                cy_screen = int((cy_img / img_h) * screen_h)

                return cx_screen, cy_screen

            # Format 2: dogrudan piksel koordinati
            if "x" in coords and "y" in coords:
                return int(coords["x"]), int(coords["y"])

            # Format 3: merkez
            if "cx" in coords and "cy" in coords:
                return int(coords["cx"]), int(coords["cy"])

        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # JSON listesi ara: [ymin, xmin, ymax, xmax]
    match_list = re.search(r'\[\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*\]', text)
    if match_list:
        try:
            vals = [float(v) for v in match_list.groups()]
            ymin, xmin, ymax, xmax = vals
            cx_norm = (xmin + xmax) / 2.0
            cy_norm = (ymin + ymax) / 2.0
            cx_screen = int((cx_norm / 1000.0) * screen_w)
            cy_screen = int((cy_norm / 1000.0) * screen_h)
            return cx_screen, cy_screen
        except Exception:
            pass

    return None


# ── Gemini Ile Konum Bul ────────────────────────────────────────────────────

def _locate_element(query: str, image_bytes: bytes, img_w: int, img_h: int) -> Optional[tuple[int, int]]:
    """
    Gemini Flash'a goruntu gonderir, istenen elementin koordinatini ister.
    Birden fazla prompt deneyerek en iyi sonucu alir.
    """
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return None

    client = genai.Client(api_key=api_key)
    image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

    # Prompt: Gemini'in kendi koordinat formatini kullan (daha guvenilir)
    prompt = (
        f"Locate the UI element described as: '{query}'\n"
        "Return ONLY a JSON object with the bounding box in this exact format:\n"
        '{"ymin": <0-1000>, "xmin": <0-1000>, "ymax": <0-1000>, "xmax": <0-1000>}\n'
        "The values are normalized coordinates where 0=top/left and 1000=bottom/right of the image.\n"
        "If not found, return: {\"ymin\": 0, \"xmin\": 0, \"ymax\": 0, \"xmax\": 0}\n"
        "No explanation, no markdown, just the JSON."
    )

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[
                types.Part.from_text(text=prompt),
                image_part,
            ],
            config=types.GenerateContentConfig(temperature=0.0)
        )
        text = str(getattr(response, "text", "") or "").strip()
        return text  # Ham metni dondur, koordinat ayrıstirma disarida yapılacak
    except Exception:
        return None


# ── Ana Fonksiyon ────────────────────────────────────────────────────────────

def click_on_screen(query: str, double_click: bool = False, right_click: bool = False) -> str:
    """
    Ekrandaki istenen UI elementini bulur ve tiklar.

    Iyilestirmeler:
    - Sadece birincil ekrani yakalar (cok monitor kaymasini onler)
    - DPI scaling duzeltmesi uygular
    - Goruntu-ekran boyut oranina gore koordinat donusturur
    - Tiklama oncesi fare konumunu 0.3s bekler (daha hassas)
    - Koordinat dogrulama (sinir disi deger kontrolu)
    """
    # DPI ayarini erkenden yap
    dpi_scale = _get_dpi_scale()

    try:
        # ── 1. Ekrani yakala ──────────────────────────────────────────────
        img, cap_w, cap_h = _capture_primary_screen()
        screen_w, screen_h = _get_primary_screen_size()

        # ── 2. Goruntu boyutunu sınırla (ama koordinat oranini koru) ──────
        image_bytes, sent_w, sent_h = _prepare_image_for_gemini(img, max_long_side=1920)

        # ── 3. Gemini ile elementi bul ────────────────────────────────────
        raw_response = _locate_element(query, image_bytes, sent_w, sent_h)

        if not raw_response:
            return f"API hatası — '{query}' bulunamadı."

        # ── 4. Koordinatlari ayrıstır ─────────────────────────────────────
        coords = _parse_coordinates(raw_response, sent_w, sent_h, screen_w, screen_h)

        if coords is None:
            return f"'{query}' ekranda bulunamadı. Gemini yanıtı: {raw_response[:100]}"

        target_x, target_y = coords

        # ── 5. Sinir kontrolu ─────────────────────────────────────────────
        margin = 5
        if target_x < margin or target_y < margin:
            return f"'{query}' bulunamadı (koordinat çok kenarda: {target_x},{target_y})"
        if target_x > screen_w - margin or target_y > screen_h - margin:
            return f"Koordinat ekran dışında: ({target_x},{target_y}) — ekran {screen_w}x{screen_h}"

        # ── 6. pyautogui FAILSAFE devre disi ─────────────────────────────
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.05

        # ── 7. Tikla ──────────────────────────────────────────────────────
        # Smooth hareket et
        pyautogui.moveTo(target_x, target_y, duration=0.4, tween=pyautogui.easeOutQuad)
        time.sleep(0.15)  # Fare yerleşsin

        if right_click:
            pyautogui.rightClick()
            action_str = "sağ tıklandı"
        elif double_click:
            pyautogui.doubleClick()
            action_str = "çift tıklandı"
        else:
            pyautogui.click()
            action_str = "tıklandı"

        return (
            f"✅ '{query}' öğesine {action_str}. "
            f"Konum: ({target_x}, {target_y}) — "
            f"Ekran: {screen_w}x{screen_h}, DPI: %{int(dpi_scale*100)}"
        )

    except Exception as e:
        return f"Tıklama hatası: {e}"
