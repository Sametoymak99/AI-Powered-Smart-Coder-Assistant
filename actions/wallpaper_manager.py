import ctypes
import os
from pathlib import Path
from weather import get_weather_summary

def set_wallpaper(image_path: str):
    """Windows duvar kağıdını değiştirir."""
    path = os.path.abspath(image_path)
    if not os.path.exists(path):
        print(f"Hata: Dosya bulunamadı {path}")
        return False
    # SPI_SETDESKWALLPAPER = 20
    # SPIF_UPDATEINIFILE = 0x01
    # SPIF_SENDCHANGE = 0x02
    result = ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
    return result != 0

def sync_wallpaper_with_weather():
    """Hava durumuna göre duvar kağıdını günceller."""
    summary = get_weather_summary()
    print(f"Hava Durumu: {summary}")
    
    # Varsayılan olarak clear kullan
    img_name = "clear.png"
    
    if "yağmur" in summary.lower() or "rain" in summary.lower():
        img_name = "rain.png"
    elif "bulut" in summary.lower() or "cloud" in summary.lower():
        img_name = "cloudy.png"
    elif "kar" in summary.lower() or "snow" in summary.lower():
        img_name = "snow.png"
        
    base_dir = Path("c:/Users/samet/OneDrive/Masaüstü/jarvis")
    img_path = base_dir / "wallpapers" / img_name
    
    # Eğer özel resim yoksa mevcut olanı (clear.png) kullan
    if not img_path.exists():
        img_path = base_dir / "wallpapers" / "clear.png"
        
    if img_path.exists():
        success = set_wallpaper(str(img_path))
        if success:
            return f"Hava durumuna göre duvar kağıdı güncellendi ({img_name})."
        return "Duvar kağıdı değiştirilemedi (API hatası)."
    return "Duvar kağıdı dosyası bulunamadı."

if __name__ == "__main__":
    print(sync_wallpaper_with_weather())
