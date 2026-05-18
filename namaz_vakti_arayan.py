import requests
import time
import datetime
import webbrowser
import pyautogui

# WhatsApp'tan aranacak kişinin numarası (Senin numaran)
HEDEF_NUMARA = "+905537711924"

def get_prayer_times(city="Istanbul", country="Turkey"):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {city} için Diyanet/Uluslararası namaz vakitleri çekiliyor...")
    # Aladhan API, tamamen ücretsiz ve güvenilir bir namaz vakti API'sidir.
    url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=13"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        timings = data['data']['timings']
        
        # Sadece temel 5 vakti alıyoruz
        vakitler = {
            "Sabah": timings["Fajr"],
            "Öğle": timings["Dhuhr"],
            "İkindi": timings["Asr"],
            "Akşam": timings["Maghrib"],
            "Yatsı": timings["Isha"]
        }
        return vakitler
    except Exception as e:
        print(f"Hata: API'den veriler alınamadı! {e}")
        return None

def make_whatsapp_call(phone_number):
    print("WhatsApp açılıyor ve arama başlatılıyor...")
    
    # WhatsApp Desktop uygulamasında hedef numarayla olan sohbeti otomatik açar
    webbrowser.open(f"whatsapp://send?phone={phone_number}")
    
    # WhatsApp'ın açılması ve sohbetin yüklenmesi için 5 saniye bekle
    time.sleep(5) 
    
    print("Sesli Arama kısayolu gönderiliyor...")
    # Yeni WhatsApp Desktop uygulamasında Sesli Arama kısayolu genellikle Ctrl + Alt + V'dir.
    # (Görüntülü arama için Ctrl + Shift + V kullanılır)
    pyautogui.hotkey('ctrl', 'alt', 'v')
    
    print("Arama tetiklendi!")

def main():
    print("🕌 Namaz Vakti WhatsApp Otonom Arama Sistemi Başlatıldı 🕌")
    print("-----------------------------------------------------------")
        
    bugun_vakitler = get_prayer_times()
    if not bugun_vakitler:
        print("Vakitler alınamadığı için sistem kapatılıyor.")
        return
        
    print("\nBugünün Vakitleri:")
    for isim, saat in bugun_vakitler.items():
        print(f"  - {isim}: {saat}")
        
    print("\nSistem arka planda saati takip ediyor. Vakit gelince WhatsApp'tan arayacak...")
    
    aranan_vakitler = [] # Aynı vakitte peş peşe arama yapmamak için takip listesi

    while True:
        simdi = datetime.datetime.now().strftime("%H:%M")
        
        for isim, saat in bugun_vakitler.items():
            # Eğer saat eşleşirse ve bugün o vakit için daha önce arama YAPILMADIYSA
            if simdi == saat and isim not in aranan_vakitler:
                print(f"\n[!] VAKİT GELDİ: {isim} namazı vakti! Saat: {saat}")
                make_whatsapp_call(HEDEF_NUMARA)
                aranan_vakitler.append(isim)
                
        # Gece yarısı olduğunda yeni günün vakitlerini çek ve takip listesini sıfırla
        if simdi == "00:01" and len(aranan_vakitler) > 0:
            print("\nYeni gün başladı. Vakitler güncelleniyor...")
            bugun_vakitler = get_prayer_times()
            aranan_vakitler = []
            time.sleep(60) # Aynı dakikada tekrar tekrar güncellememesi için bekle
            
        # İşlemciyi yormamak için her 30 saniyede bir kontrol et
        time.sleep(30)

if __name__ == "__main__":
    main()
