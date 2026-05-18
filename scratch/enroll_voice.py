"""
scratch/enroll_voice.py — Ses izi kayıt betiği
"""
import os
import sys
import time
import numpy as np
import sounddevice as sd

# Proje kök dizinini path'e ekle
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from actions.voice_auth import calculate_spectrogram, save_fingerprint

SAMPLE_RATE = 16000
DURATION = 2.0  # Saniye

def record_audio(duration=DURATION, samplerate=SAMPLE_RATE):
    """Sesi kaydeder."""
    print("Kayıt başlıyor... Konuşun!")
    audio = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='float32')
    sd.wait()
    print("Kayıt bitti.")
    return audio.flatten()

def main():
    print("==================================================")
    print("        F.R.I.D.A.Y. SES İZİ KAYIT SİSTEMİ        ")
    print("==================================================")
    print("Lütfen 'Friday' kelimesini 3 kez söyleyin.\n")
    
    specs = []
    for i in range(3):
        input(f"{i+1}. kayıt için ENTER'a basın ve 'Friday' deyin...")
        audio = record_audio()
        spec = calculate_spectrogram(audio)
        specs.append(spec)
        time.sleep(0.5)
        
    # Spektrogramların ortalamasını al
    # Boyutları farklı olabileceği için zaman ekseninde ortalamalarını alıp öyle birleştirelim
    profiles = [np.mean(s, axis=0) for s in specs]
    avg_profile = np.mean(profiles, axis=0)
    
    # Ortalama profili bir spektrogram gibi kaydedelim (1 x freq_bins)
    avg_spec = np.expand_dims(avg_profile, axis=0)
    
    save_fingerprint(avg_spec)
    print("\n[BAŞARILI] Ses iziniz kaydedildi!")
    print("Artık F.R.I.D.A.Y. sadece sizi dinleyecek.")

if __name__ == "__main__":
    main()
