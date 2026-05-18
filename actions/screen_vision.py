# F.R.I.D.A.Y Windows Edition
from __future__ import annotations

import io
import time
import os
import tempfile
from pathlib import Path

from PIL import ImageGrab, Image
from google import genai
from google.genai import types

from app_config import get_app_config_value

def capture_screen_image() -> tuple[bool, str, Path | None]:
    try:
        # Tüm ekranları veya birincil ekranı yakalar (Windows uyumlu)
        img = ImageGrab.grab(all_screens=True)
        
        handle = tempfile.NamedTemporaryFile(prefix="jarvis-screen-", suffix=".png", delete=False)
        image_path = Path(handle.name)
        handle.close()
        
        img.save(str(image_path), format="PNG")
        return True, "", image_path
    except Exception as e:
        return False, f"Ekran görüntüsü alınamadı: {e}", None

def _vision_prompt(query: str) -> str:
    user_query = (query or "Ekranda ne var?").strip()
    return (
        "Sen F.R.I.D.A.Y için çalışan, bilgisayar ekranını okuyabilen bir yapay zekasın.\n"
        "Aşağıdaki görüntü bilgisayar ekranından yeni alındı.\n\n"
        "Görevlerin:\n"
        "1. Ekranın genel bağlamını (hangi uygulamalar açık vb.) kısaca anla.\n"
        "2. Kullanıcının sorduğu soruyu doğrudan bu görüntüye bakarak cevapla.\n"
        "3. Ekranda bir hata, bildirim veya okuman istenen bir metin varsa detaylıca oku ve açıkla.\n\n"
        f"Kullanıcı sorusu: {user_query}\n\n"
        "Yanıtı Türkçe, kısa, net ve akıcı bir asistan tonuyla ver."
    )

def _build_image_part(image_path: Path) -> types.Part:
    try:
        with Image.open(image_path) as img:
            work = img.convert("RGB")
            max_dim = 1500
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

def analyze_screen(query: str, target: str = "active_window") -> str:
    ok, error_msg, image_path = capture_screen_image()
    if not ok or not image_path:
        return error_msg
        
    try:
        api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
        if not api_key:
            return "Gemini API anahtarı eksik olduğu için ekran analizi yapılamadı."

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
            return f"[Ekran Analizi] {text.strip()}"
        return "Ekran görüntüsü analiz edilemedi."
        
    except Exception as exc:
        return f"Ekran analizi başarısız oldu: {exc}"
    finally:
        try:
            if image_path and image_path.exists():
                image_path.unlink()
        except Exception:
            pass
