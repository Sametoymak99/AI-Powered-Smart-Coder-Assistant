import os

def read_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        return f"Hata: Dosya bulunamadı: {filepath}"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Eğer dosya çok uzunsa, başını ve sonunu gösterip kes
        if len(content) > 10000:
            truncated = content[:4000] + "\n\n... [İÇERİK ÇOK UZUN, KESİLDİ] ...\n\n" + content[-4000:]
            return f"Dosya okundu (kısaltılmış - {filepath}):\n\n{truncated}"
            
        return f"Dosya okundu ({filepath}):\n\n{content}"
    except Exception as e:
        return f"Dosya okunamadı: {str(e)}"

def write_file(filepath: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Dosya başarıyla yazıldı: {filepath}"
    except Exception as e:
        return f"Yazma hatası: {str(e)}"

def replace_code(filepath: str, target: str, replacement: str) -> str:
    if not os.path.exists(filepath):
        return f"Hata: Dosya bulunamadı: {filepath}"
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if target not in content:
            return "Hata: Değiştirilmek istenen hedef (target) kod bloğu dosyada tam olarak bulunamadı. Lütfen boşlukların ve satır atlamaların harfi harfine aynı olduğundan emin olun."
            
        new_content = content.replace(target, replacement, 1) # Sadece ilk eşleşeni değiştir
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return f"Kod başarıyla değiştirildi: {filepath}"
    except Exception as e:
        return f"Değiştirme hatası: {str(e)}"

import subprocess
import tempfile
import sys

def execute_code(code_str: str = "", filepath: str = "") -> str:
    """Belirtilen python kodunu veya dosyasını çalıştırır."""
    if filepath and os.path.exists(filepath):
        target_file = filepath
    elif code_str:
        fd, target_file = tempfile.mkstemp(suffix=".py")
        os.close(fd)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(code_str)
    else:
        return "Çalıştırılacak kod veya dosya belirtilmedi."

    try:
        result = subprocess.run([sys.executable, target_file], capture_output=True, text=True, timeout=30)
        output = result.stdout
        if result.stderr:
            output += "\n--- ERROR ---\n" + result.stderr
            
        return f"Kod çalıştırıldı. Çıktı:\n{output}" if output else "Kod başarıyla çalıştı (Çıktı yok)."
    except subprocess.TimeoutExpired:
        return "Kod çalıştırma zaman aşımına uğradı (30s)."
    except Exception as e:
        return f"Çalıştırma hatası: {e}"
    finally:
        if code_str and not filepath and os.path.exists(target_file):
            try:
                os.remove(target_file)
            except:
                pass

def run_tests(target_path: str = ".") -> str:
    """Belirtilen dizinde veya dosyada pytest çalıştırır."""
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", target_path], capture_output=True, text=True, timeout=60)
        return f"Test Sonuçları:\n{result.stdout}\n{result.stderr}"
    except Exception as e:
        return f"Test çalıştırma hatası: {e}"
