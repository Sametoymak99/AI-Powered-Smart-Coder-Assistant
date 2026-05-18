"""
actions/voice_auth.py — Ses biyometrisi ve doğrulama
"""
import os
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FINGERPRINT_FILE = BASE_DIR / "memory" / "voice_fingerprint.npy"

def calculate_spectrogram(audio_data: np.ndarray, n_fft: int = 512, hop_length: int = 256) -> np.ndarray:
    """Saf NumPy kullanarak ses verisinin spektrogramını hesaplar."""
    if len(audio_data) < n_fft:
        return np.zeros((1, n_fft // 2))
        
    # Sinyali pencerelere böl ve FFT uygula
    frames = []
    for i in range(0, len(audio_data) - n_fft, hop_length):
        frame = audio_data[i:i+n_fft]
        # Hanning penceresi uygula
        window = np.hanning(len(frame))
        windowed_frame = frame * window
        # FFT hesapla
        fft_res = np.fft.fft(windowed_frame)
        # Sadece pozitif frekansları ve büyüklüklerini al
        magnitude = np.abs(fft_res[:n_fft//2])
        frames.append(magnitude)
    
    if not frames:
        return np.zeros((1, n_fft // 2))
        
    return np.array(frames)

def compare_spectrograms(spec1: np.ndarray, spec2: np.ndarray) -> float:
    """İki spektrogram arasındaki benzerliği (Cosine Similarity) hesaplar."""
    # Zaman ekseninde ortalama alarak "frekans profilini" karşılaştıralım (Boyut eşitlemek için)
    prof1 = np.mean(spec1, axis=0)
    prof2 = np.mean(spec2, axis=0)
    
    # Cosine similarity
    dot = np.dot(prof1, prof2)
    norm1 = np.linalg.norm(prof1)
    norm2 = np.linalg.norm(prof2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def save_fingerprint(spectrogram: np.ndarray):
    """Ses izini kaydeder."""
    os.makedirs(FINGERPRINT_FILE.parent, exist_ok=True)
    np.save(FINGERPRINT_FILE, spectrogram)

def load_fingerprint() -> np.ndarray | None:
    """Ses izini yükler."""
    if os.path.exists(FINGERPRINT_FILE):
        return np.load(FINGERPRINT_FILE)
    return None

def verify_speaker(audio_data: np.ndarray, threshold: float = 0.85) -> tuple[bool, float]:
    """Gelen sesin kayıtlı ses iziyle uyuşup uyuşmadığını kontrol eder."""
    # Kullanıcı talebi üzerine ses doğrulama devre dışı bırakıldı (Her zaman True döner).
    return True, 1.0
