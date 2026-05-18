from __future__ import annotations
import os
from pathlib import Path
from google import genai
from google.genai import types

from app_config import get_app_config_value
from actions.email_manager import read_emails
from actions.notifications import get_notification_summary

def get_daily_briefing() -> str:
    """
    E-postaları ve Windows bildirimlerini toplar, Gemini ile özetler.
    """
    # 1. Verileri Topla
    try:
        emails = read_emails(count=5, unread_only=True)
    except Exception as e:
        emails = f"E-postalar okunamadı: {e}"
        
    try:
        notifications = get_notification_summary()
    except Exception as e:
        notifications = f"Bildirimler okunamadı: {e}"
        
    # 2. Gemini ile Özetle
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return "Gemini API anahtarı eksik olduğu için brifing hazırlanamadı."
        
    client = genai.Client(api_key=api_key)
    
    prompt = (
        "Sen F.R.I.D.A.Y.'sin. Aşağıda kullanıcının bilgisayarından toplanan e-posta ve bildirim verileri yer almaktadır.\n"
        "Senin görevin bu verileri analiz etmek ve kullanıcıya samimi, profesyonel ve net bir 'Günlük Brifing' (Sabah Özeti) sunmaktır.\n\n"
        "Kurallar:\n"
        "1. Önemli e-postaları (kimden geldiğini ve konusunu) belirt.\n"
        "2. Çok fazla bildirim varsa gruplayarak özetle (Örn: 'WhatsApp'tan 5 yeni mesajınız var').\n"
        "3. Yanıtı Türkçe ve sesli okunmaya uygun (akıcı) bir şekilde ver.\n"
        "4. Eğer okunmamış e-posta veya bildirim yoksa, dürüstçe söyle ve günün güzel geçmesini dile.\n\n"
        f"--- GELEN E-POSTALAR ---\n{emails}\n\n"
        f"--- BİLDİRİMLER ---\n{notifications}\n\n"
        "Brifing:"
    )
    
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(
                temperature=0.5,
            ),
        )
        
        text = str(getattr(response, "text", "") or "").strip()
        if text:
            return text
        return "Brifing oluşturulamadı (Boş yanıt)."
        
    except Exception as e:
        return f"Brifing oluşturulurken hata oluştu: {e}"

if __name__ == "__main__":
    # Test amaçlı doğrudan çalıştırılabilir
    print("Günlük Brifing hazırlanıyor...\n")
    print(get_daily_briefing())
