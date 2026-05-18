from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
import sys

COMMON_APPS = {
    "spotify": "Spotify.exe",
    "chrome": "chrome.exe",
    "discord": "Discord.exe",
    "brave": "brave.exe",
    "edge": "msedge.exe"
}

def set_app_volume(app_name: str, volume_percent: int):
    """
    Belirli bir uygulamanın ses seviyesini ayarlar.
    app_name: Uygulama adı (örn: spotify veya Spotify.exe)
    volume_percent: 0-100 arası ses seviyesi
    """
    # Yaygın isimleri exe'ye çevir
    lookup = app_name.lower()
    exe_name = COMMON_APPS.get(lookup, app_name)
    if not exe_name.lower().endswith(".exe"):
        exe_name += ".exe"
        
    sessions = AudioUtilities.GetAllSessions()
    found = False
    for session in sessions:
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        if session.Process and session.Process.name().lower() == exe_name.lower():
            volume.SetMasterVolume(volume_percent / 100.0, None)
            found = True
            print(f"{exe_name} sesi %{volume_percent} yapıldı.")
            
    if not found:
        print(f"{exe_name} uygulaması bulunamadı veya aktif ses oturumu yok.")
        return f"{exe_name} bulunamadı veya ses çalmıyor."
        
    return f"{exe_name} sesi %{volume_percent} yapıldı."

if __name__ == "__main__":
    if len(sys.argv) > 2:
        app = sys.argv[1]
        vol = int(sys.argv[2])
        print(set_app_volume(app, vol))
    else:
        print("Kullanım: py volume_manager.py [uygulama_adi] [ses_yuzdesi]")
