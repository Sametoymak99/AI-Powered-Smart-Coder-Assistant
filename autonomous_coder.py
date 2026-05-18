import os
import subprocess
import time
import socket
import urllib.request
import json
from google import genai
from google.genai import types
from app_config import get_app_config_value

def is_ollama_running() -> bool:
    """Yerel Ollama servisinin aktif olup olmadığını hızlıca kontrol eder."""
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1):
            return True
    except OSError:
        return False

def get_installed_ollama_models() -> list[str]:
    """Sistemde yüklü olan tüm Ollama modellerini çeker."""
    try:
        url = "http://127.0.0.1:11434/api/tags"
        with urllib.request.urlopen(url, timeout=2) as response:
            res = json.loads(response.read().decode("utf-8"))
            return [m["name"] for m in res.get("models", [])]
    except Exception:
        return []

def query_ollama(prompt: str, model: str) -> str:
    """Urllib standard kütüphanesi kullanarak yerel Ollama LLM modeline istek atar."""
    url = "http://127.0.0.1:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        res = json.loads(response.read().decode("utf-8"))
        return res.get("response", "").strip()

def generate_and_run_code(task: str, max_retries: int = 3) -> str:
    """
    Kullanıcının istediği göreve göre kod üretir, çalıştırır ve hata varsa düzeltir.
    Gemini kotası dolduğunda veya hata verdiğinde yerel Ollama servisine otomatik fallback yapar.
    """
    filepath = "generated_project.py"
    
    # Ollama algılama ve model seçimi
    ollama_active = is_ollama_running()
    ollama_models = get_installed_ollama_models() if ollama_active else []
    
    selected_ollama_model = None
    # Öncelikle kod üretimi için en iyi modelleri ara
    for m in ollama_models:
        if any(x in m.lower() for x in ["coder", "qwen", "deepseek", "llama", "gemma"]):
            selected_ollama_model = m
            break
    if ollama_models and not selected_ollama_model:
        selected_ollama_model = ollama_models[0] # Yüklü ilk modeli seç

    backend_pref = get_app_config_value("coder_backend", "auto")
    use_ollama = (backend_pref == "ollama") or (backend_pref == "auto" and not get_app_config_value("gemini_api_key"))
    
    prompt = (
        f"Sen fütüristik yapay zeka asistanı F.R.I.D.A.Y.'in kod yazma modülüsün.\n"
        f"Kullanıcının şu isteğini yerine getiren bir Python kodu yaz:\n"
        f"'{task}'\n\n"
        f"Kurallar:\n"
        f"1. Sadece KODU döndür. Markdown (```python) kullanma, sadece saf python kodu olsun.\n"
        f"2. Kod kendi kendine çalışabilir olmalı ve gerekli kütüphaneleri (eğer standart dışıysa) try-except ile kontrol etmeli.\n"
        f"3. Kodun çıktısını temiz bir şekilde yazdır.\n"
        f"4. Kod karmaşık olmasın, amaca yönelik ve çalışır durumda olsun."
    )
    
    current_prompt = prompt
    active_engine_name = "Gemini 2.5 Flash"
    
    for i in range(max_retries):
        print(f"Döngü {i+1}: Kod üretiliyor...")
        code = ""
        
        # Eğer Ollama zorunlu seçilmişse veya Gemini patlamışsa
        if use_ollama and selected_ollama_model:
            active_engine_name = f"Ollama ({selected_ollama_model})"
            print(f"[CODER] Yerel Ollama kullanılıyor: {selected_ollama_model}")
            try:
                code = query_ollama(current_prompt, selected_ollama_model)
            except Exception as e:
                return f"❌ Yerel Ollama istek hatası: {e}"
        else:
            api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
            if not api_key:
                if ollama_active and selected_ollama_model:
                    use_ollama = True
                    active_engine_name = f"Ollama ({selected_ollama_model}) [Auto Fallback]"
                    print("[CODER] Gemini API Anahtarı eksik, yerel Ollama'ya otomatik geçiş yapıldı.")
                    try:
                        code = query_ollama(current_prompt, selected_ollama_model)
                    except Exception as e:
                        return f"❌ Yerel Ollama istek hatası: {e}"
                else:
                    return "❌ Gemini API anahtarı eksik ve sistemde aktif yerel Ollama (Llama/Qwen) servisi bulunamadı."
            else:
                # Gemini API çağrısı
                client = genai.Client(api_key=api_key)
                try:
                    response = client.models.generate_content(
                        model="models/gemini-2.5-flash",
                        contents=[types.Part.from_text(text=current_prompt)],
                    )
                    code = str(getattr(response, "text", "") or "").strip()
                except Exception as e:
                    err_str = str(e)
                    # Limit aşımı veya 429 kontrolü
                    if ("429" in err_str or "limit" in err_str.lower() or "exhausted" in err_str.lower()) and ollama_active and selected_ollama_model:
                        print("[CODER] ⚠️ Gemini API limiti aşıldı! Otomatik olarak yerel Ollama modeline geçiliyor...")
                        use_ollama = True
                        active_engine_name = f"Ollama ({selected_ollama_model}) [Rate-Limit Fallback]"
                        try:
                            code = query_ollama(current_prompt, selected_ollama_model)
                        except Exception as o_err:
                            return f"❌ Gemini API limiti aşıldı ve yerel Ollama da başarısız oldu: {o_err}"
                    else:
                        # Üst üste istek durumunda kısa bekleme yap
                        if i < max_retries - 1:
                            print("[CODER] İstek limitine takılındı. 4 saniye beklenip yeniden denenecek...")
                            time.sleep(4)
                            continue
                        else:
                            return f"❌ Gemini API Çağrı Hatası: {e}"
                            
        # Markdown temizleme (eğer model kurala uymadıysa)
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        if code.endswith("```"):
            code = code[:-3]
        code = code.strip()
        
        # Kodu dosyaya kaydet
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
            
        print(f"Kod kaydedildi. Çalıştırılıyor...")
        
        # Kodu çalıştır
        result = subprocess.run(
            ["py", filepath],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return (f"✅ Proje başarıyla tamamlandı ve çalıştırıldı! [Motor: {active_engine_name}]\n\n"
                    f"Çalışan Kod:\n```python\n{code}\n```\n\nÇıktı:\n{result.stdout}")
        else:
            print(f"Hata alındı. Kendi kendini düzeltme başlıyor...")
            # Hata durumunda promptu güncelle
            current_prompt = (
                f"Yazdığın kod hata verdi. Lütfen hatayı düzeltip kodu tekrar yaz.\n\n"
                f"Orijinal İstek: {task}\n\n"
                f"Yazdığın Kod:\n{code}\n\n"
                f"Hata Çıktısı:\n{result.stderr}\n\n"
                f"Sadece düzeltilmiş saf python kodunu döndür. Markdown kullanma."
            )
            
    return f"❌ {max_retries} denemede çalışan kod üretilemedi. Son hatayı düzeltemedim. [Motor: {active_engine_name}]"
