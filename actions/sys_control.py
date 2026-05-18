"""
System Control functions (Volume, Brightness)
"""
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER

def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    try:
        import comtypes
        try: comtypes.CoInitialize()
        except Exception: pass
        devices = AudioUtilities.GetSpeakers()
        
        # pycaw'ın modern sürümlerinde EndpointVolume doğrudan bir özelliktir.
        if hasattr(devices, "EndpointVolume"):
            volume = devices.EndpointVolume
        else:
            # Eski pycaw sürümleri için raw IMMDevice üzerinden etkinleştirme
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        # Scalar volume is 0.0 to 1.0
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Ses seviyesi %{level} olarak ayarlandı."
    except Exception as e:
        return f"Ses seviyesi ayarlanamadı: {e}"

def get_volume() -> int:
    try:
        import comtypes
        try: comtypes.CoInitialize()
        except Exception: pass
        devices = AudioUtilities.GetSpeakers()
        
        if hasattr(devices, "EndpointVolume"):
            volume = devices.EndpointVolume
        else:
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            
        return int(volume.GetMasterVolumeLevelScalar() * 100)
    except Exception:
        return 50

def set_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))
    try:
        sbc.set_brightness(level)
        return f"Ekran parlaklığı %{level} olarak ayarlandı."
    except Exception as e:
        return f"Ekran parlaklığı ayarlanamadı: {e}"
