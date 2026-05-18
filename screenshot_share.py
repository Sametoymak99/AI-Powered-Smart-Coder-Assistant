import time
import pyautogui
import subprocess
from pathlib import Path
from actions.whatsapp import send_whatsapp_message

def take_ss_and_share(recipient_name: str):
    base_dir = Path("c:/Users/samet/OneDrive/Masaüstü/jarvis")
    filepath = base_dir / "screenshot.jpg"
    
    # 1. Ekran görüntüsü al
    pyautogui.screenshot(str(filepath))
    
    # 2. WhatsApp'ı aç (Numara yoksa isimle arar)
    send_whatsapp_message(message="Ekran görüntüsü gönderiliyor...", recipient_name=recipient_name, send_now=True)
    
    # 3. Resmi panoya kopyala (Windows)
    ps_cmd = f'Add-Type -AssemblyName System.Windows.Forms; $img = [System.Drawing.Image]::FromFile("{str(filepath)}"); [System.Windows.Forms.Clipboard]::SetImage($img)'
    try:
        subprocess.run(["powershell", "-Command", ps_cmd], check=True)
    except Exception as e:
        return f"Resim panoya kopyalanamadı: {e}"
    
    # 4. WhatsApp'ın açılmasını bekle (Süre artırıldı)
    time.sleep(10)
    
    # 5. Yapıştır ve Gönder
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)
    pyautogui.press('enter')
    
    return f"Ekran görüntüsü alındı ve {recipient_name} kişisine gönderiliyor."

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(take_ss_and_share(sys.argv[1]))
    else:
        print("Kullanım: py screenshot_share.py [Kişi Adı]")
