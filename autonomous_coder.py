import os
import sys
import subprocess
import time
import socket
import urllib.request
import urllib.parse
import json
import re
from google import genai
from google.genai import types
from app_config import get_app_config_value
from actions.github_manager import push_to_github, create_and_push_new_project, create_branch_and_pr

# ── Windows CP-1254 / emoji UnicodeEncodeError düzeltmesi ──────────────────
# Konsol UTF-8 desteği yoksa (örn. Windows cmd/PowerShell), print() emoji'leri
# çöker. stdout/stderr'i UTF-8 moduna alarak tüm emoji'lerin güvenle yazılmasını sağla.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def is_ollama_running() -> bool:
    """Yerel Ollama servisinin aktif olup olmadığını hızlıca kontrol eder."""
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=2):
            return True
    except (OSError, socket.timeout, ConnectionRefusedError):
        # Localhost değil de 0.0.0.0:11434 dinliyor olabilir, bir de onu dene
        try:
            with socket.create_connection(("localhost", 11434), timeout=2):
                return True
        except:
            return False

def get_installed_ollama_models() -> list[str]:
    """Sistemde yüklü olan tüm Ollama modellerini çeker."""
    for host in ["127.0.0.1", "localhost"]:
        try:
            url = f"http://{host}:11434/api/tags"
            with urllib.request.urlopen(url, timeout=3) as response:
                res = json.loads(response.read().decode("utf-8"))
                models = [m["name"] for m in res.get("models", [])]
                if models:
                    return models
        except Exception:
            continue
    return []

def query_ollama(prompt: str, model: str, stream: bool = True) -> str:
    """Urllib standard kütüphanesi kullanarak yerel Ollama LLM modeline istek atar."""
    url = "http://127.0.0.1:11434/api/generate"
    data = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    full_response = ""
    if stream:
        print("\n[OLLAMA YAZIYOR]: ", end="", flush=True)
        with urllib.request.urlopen(req, timeout=120) as response:
            for line in response:
                if line:
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                        text = chunk.get("response", "")
                        full_response += text
                        print(text, end="", flush=True)
                    except Exception:
                        pass
        print("\n")
    else:
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                res = json.loads(response.read().decode("utf-8"))
                full_response = res.get("response", "")
        except Exception as e:
            print(f"[OLLAMA HATA]: {e}")
    return full_response.strip()

def search_duckduckgo(query: str, max_results: int = 3) -> str:
    """DuckDuckGo Lite HTML sitesinden arama sorgusu sonuçlarını çeker ve temiz metin olarak döndürür."""
    try:
        encoded_query = urllib.parse.quote_plus(query)
        url = "https://lite.duckduckgo.com/lite/"
        data = f"q={encoded_query}".encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="ignore")
            
            snippets = re.findall(r'<td class="result-snippet">\s*(.*?)\s*</td>', html, re.DOTALL)
            links = re.findall(r'<a class="result-link" href=".*?">\s*(.*?)\s*</a>', html, re.DOTALL)
            
            results = []
            for i in range(min(len(snippets), max_results)):
                clean_snippet = re.sub(r'<[^>]*>', '', snippets[i]).strip()
                clean_link_title = re.sub(r'<[^>]*>', '', links[i]).strip() if i < len(links) else ""
                results.append(f"Sonuç {i+1}: {clean_link_title}\nÖzet: {clean_snippet}")
                
            if not results:
                return "Arama sonucunda anlamlı bir bilgi bulunamadı."
            return "\n\n".join(results)
    except Exception as e:
        return f"Arama sırasında hata oluştu: {e}"

def parse_multi_files(output_text: str) -> dict[str, str]:
    """
    Model çıktısını tarayarak 'FILE: dosya_adi.py' ve altındaki kod bloğunu ayıklar.
    Geriye {dosya_adi: kod_icerigi} şeklinde bir dict döndürür.
    # FILE: veya ### FILE: kullanımlarını da destekler.
    """
    files = {}
    pattern = r'(?:#|###)?\s*FILE:\s*([a-zA-Z0-9_\-\.\/]+)'
    matches = list(re.finditer(pattern, output_text))
    
    if matches:
        for i, match in enumerate(matches):
            filename = match.group(1).strip()
            start_idx = match.end()
            end_idx = matches[i+1].start() if i + 1 < len(matches) else len(output_text)
            
            content = output_text[start_idx:end_idx].strip()
            
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                if line.strip().startswith('```'):
                    continue
                cleaned_lines.append(line)
            
            if filename:
                files[filename] = '\n'.join(cleaned_lines).strip()
    else:
        content = output_text
        if "```python" in content:
            content = content.split("```python")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        files[""] = content.strip()
        
    return files

def generate_and_run_code(task: str, filepath: str = "generated_project.py", max_retries: int = 3) -> str:
    """
    Kullanıcının istediği göreve göre kod üretir, çalıştırır ve hata varsa düzeltir.
    Gelişmiş sandbox (venv), statik tarama (bandit/pylint) ve GitHub PR otomasyonunu barındırır.
    """
    if not filepath.strip():
        filepath = "generated_project.py"
    if not filepath.endswith(".py"):
        filepath += ".py"
        
    project_name = filepath.replace(".py", "")
    is_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    if is_github_actions:
        project_dir = os.path.abspath(os.path.join("Otonom_Projeler", project_name))
    else:
        project_dir = os.path.abspath(os.path.join("..", "Otonom_Projeler", project_name))
    os.makedirs(project_dir, exist_ok=True)
    
    full_filepath = os.path.join(project_dir, filepath)
    
    # Mevcut kodu oku (İteratif geliştirme için)
    existing_code = ""
    if os.path.exists(full_filepath):
        with open(full_filepath, "r", encoding="utf-8") as f:
            existing_code = f.read().strip()
            
    # --- Sandbox Kurulumu (Python venv) ---
    venv_dir = os.path.join(project_dir, "venv")
    if not os.path.exists(venv_dir):
        print("[CODER] 🔨 İzole sanal ortam (venv) oluşturuluyor...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], cwd=project_dir, capture_output=True)
        # Git log kirliliğini önlemek için .gitignore oluştur
        gitignore_path = os.path.join(project_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("venv/\n__pycache__/\n.pytest_cache/\n")
        
    if os.name == "nt":
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_python = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")
        
    # Güvenlik ve kalite araçlarını venv'e kur (Bandit, Pylint, Ruff)
    print("[CODER] 📦 Güvenlik ve statik analiz araçları sanal ortama kuruluyor...")
    install_res = subprocess.run([venv_pip, "install", "-q", "bandit", "pylint", "pytest", "ruff"], capture_output=True, text=True)
    if install_res.returncode != 0:
        print(f"[CODER] ⚠️ Araçlar kurulurken uyarı: {install_res.stderr[:200]}")
        # Hata olsa da devam et, en az pytest kurulmuş halde olması lazım
        subprocess.run([venv_pip, "install", "-q", "pytest"], capture_output=True)

    # Ollama algılama ve model seçimi
    ollama_active = is_ollama_running()
    ollama_models = get_installed_ollama_models() if ollama_active else []
    
    selected_ollama_model = None
    for m in ollama_models:
        if any(x in m.lower() for x in ["coder", "qwen", "deepseek", "llama", "gemma"]):
            selected_ollama_model = m
            break
    if ollama_models and not selected_ollama_model:
        selected_ollama_model = ollama_models[0]

    backend_pref = get_app_config_value("coder_backend", "auto")
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    
    # Akıllı backend seçimi: Ollama varsa ve API key yoksa Ollama'yı kullan
    use_ollama = (backend_pref == "ollama") or (backend_pref == "auto" and ollama_active and not api_key)
    
    # Eğer Ollama tercih edildiyse ama çalışmıyorsa API key'e fallback yap
    if use_ollama and not ollama_active:
        print("[CODER] ⚠️ Ollama tercih edildi fakat servisi çalışmıyor. Gemini API'ye geçiliyor...")
        use_ollama = False
    
    # Eğer ne Ollama ne API key varsa hata ver
    if not api_key and not (ollama_active and selected_ollama_model):
        return ("❌ HATA: Sistem başlatılamadı!\n"
                "Gemini API anahtarı eksik VE yerel Ollama servisi bulunmuyor/çalışmıyor.\n\n"
                "Çözüm seçenekleri:\n"
                "1. config/api_keys.json içinde 'gemini_api_key' ekle\n"
                "2. GEMINI_API_KEY ortam değişkenini ayarla\n"
                "3. Ya da: ollama serve komutunu terminalde çalıştırıp Ollama servisini başlat")

    # --- Gemini istemcisi (client) hazırla — tek seferlik, yeniden kullanılabilir ---
    client = None
    if not use_ollama and api_key:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"[CODER] ⚠️ Gemini istemcisi oluşturulamadı: {e}")

    # --- AŞAMA 1: Arama Kararı & Entegrasyonu ---
    print("[CODER] İnternet araması gerekip gerekmediği değerlendiriliyor...")
    search_decision_prompt = (
        f"GÖREV: '{task}'\n"
        f"Bu görevi yerine getirmek için internette arama yapmaya gerek var mı? (Yeni/Güncel kütüphane kullanımları, API dokümantasyonu vb. için)\n"
        f"Eğer arama yapmaya İHTİYAÇ VARSA, sadece arama motoruna yazılacak en iyi kısa İngilizce/Türkçe sorguyu yaz. Örn: 'yfinance history parameters 2026'\n"
        f"Eğer arama yapmaya İHTİYAÇ YOKSA, sadece 'HAYIR' kelimesini yaz. Başka hiçbir şey yazma."
    )
    
    search_query = ""
    if not use_ollama and client:
        try:
            res = client.models.generate_content(
                model="models/gemini-2.5-flash",
                contents=[types.Part.from_text(text=search_decision_prompt)]
            )
            decision = str(getattr(res, "text", "") or "").strip()
            if decision.upper() != "HAYIR" and len(decision) > 2:
                search_query = decision.replace('"', '').replace("'", "")
        except Exception:
            pass
    elif selected_ollama_model:
        try:
            decision = query_ollama(search_decision_prompt, selected_ollama_model, stream=False)
            if decision.upper() != "HAYIR" and len(decision) > 2:
                search_query = decision.replace('"', '').replace("'", "")
        except Exception:
            pass

    search_results = ""
    if search_query:
        print(f"[CODER] 🔍 İnternette aranıyor: '{search_query}'...")
        search_results = search_duckduckgo(search_query)
        print(f"[CODER] 📄 Arama Sonuçları alındı.")
    else:
        print(f"[CODER] İnternet aramasına ihtiyaç duyulmadı.")

    # --- AŞAMA 2: Geliştirici & Testçi Ajan Döngüsü ---
    active_engine_name = "Gemini 2.5 Flash"
    current_developer_prompt = ""
    previous_errors = ""
    
    for i in range(max_retries):
        print(f"\n🚀 İterasyon {i+1}/{max_retries} - Geliştirici Ajan çalışıyor...")
        
        prompt_intro = (
            f"Sen fütüristik yapay zeka asistanı F.R.I.D.A.Y.'in otonom Geliştirici Ajanı'sın.\n"
            f"Görevin, kullanıcının istediği projeyi en iyi şekilde kodlamak.\n\n"
            f"İSTEK: '{task}'\n"
            f"Hedef Başlangıç Dosyası: {filepath}\n"
        )
        
        if existing_code:
            prompt_intro += f"Mevcut Kod ({filepath}):\n```python\n{existing_code}\n```\n"
            
        if search_results:
            prompt_intro += f"İnternetten Alınan Dokümantasyon/Bilgiler:\n{search_results}\n\n"
            
        if previous_errors:
            prompt_intro += f"Önceki Hatalar, Güvenlik Açıkları veya Test Başarısızlıkları:\n{previous_errors}\n\nLütfen bu hataları ve güvenlik açıklarını kesinlikle düzelt."
            
        prompt_rules = (
            f"\nKESİN KURALLAR (İHLAL ETME):\n"
            f"1. ÜST DÜZEY KALİTE: Yazdığın kod profesyonel, modüler (SOLID prensiplerine uygun), ölçeklenebilir ve tamamen optimize edilmiş olmalıdır.\n"
            f"2. Her dosya EKSIKSIZ ve ÇALIŞAN Python kodu içermeli. Kesinlikle boş bırakma, 'pass', 'TODO', 'placeholder' veya taslak yazma!\n"
            f"3. Gelişmiş Type Hinting (`typing` kütüphanesi) ve detaylı Docstring'ler (Google veya Sphinx stili) kullan.\n"
            f"4. İleri Seviye Hata Yönetimi: Çok detaylı `try-except` blokları kur ve hataları doğru şekilde ele alıp raporla (Custom Exception'lar dahil).\n"
            f"5. Çoklu dosya oluşturabilirsin. Her dosyayı şu formatta ver:\n"
            f"FILE: dosya_adi.py\n"
            f"```python\n"
            f"# buraya gerçek, çalışan kod\n"
            f"```\n"
            f"6. Güvenli kod yaz — shell injection, eval(), hardcoded şifre/token KESİNLİKLE yasak.\n"
            f"7. 3. parti modüller (psutil, requests vb.) kullanıyorsan, 'requirements.txt' dosyasında KESİNLİKLE belirt.\n"
            f"8. KOD MİMARİSİ: Ana kodları mantıksal bir klasör yapısıyla 'src/' içine (örn: src/core, src/utils, src/main.py) yerleştir. Testleri 'tests/' klasörüne ekle.\n"
            f"9. DOKÜMANTASYON: Projenin kurulumunu ve mimarisini detaylıca anlatan profesyonel bir 'README.md' dosyası oluştur."
        )
        
        current_developer_prompt = prompt_intro + prompt_rules
        
        code_output = ""
        if use_ollama and selected_ollama_model:
            active_engine_name = f"Ollama ({selected_ollama_model})"
            try:
                code_output = query_ollama(current_developer_prompt, selected_ollama_model)
            except Exception as e:
                return f"❌ Yerel Ollama istek hatası: {e}"
        else:
            if not api_key:
                return "❌ Gemini API anahtarı eksik ve sistemde aktif yerel Ollama servisi bulunamadı."
            # client yoksa (arama fazında oluşturulamadıysa) yeniden dene
            if client is None:
                try:
                    client = genai.Client(api_key=api_key)
                except Exception as e:
                    return f"❌ Gemini istemcisi oluşturulamadı: {e}"
            try:
                print("\n[GEMINI YAZIYOR]: ", end="", flush=True)
                response = client.models.generate_content_stream(
                    model="models/gemini-2.5-flash",
                    contents=[types.Part.from_text(text=current_developer_prompt)],
                )
                for chunk in response:
                    text = str(getattr(chunk, "text", "") or "")
                    code_output += text
                    print(text, end="", flush=True)
                print("\n")
                code_output = code_output.strip()
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "limit" in err_str.lower() or "exhausted" in err_str.lower()) and ollama_active and selected_ollama_model:
                    print("[CODER] ⚠️ Gemini API limiti aşıldı! Otomatik olarak yerel Ollama modeline geçiliyor...")
                    use_ollama = True
                    active_engine_name = f"Ollama ({selected_ollama_model}) [Rate-Limit Fallback]"
                    try:
                        code_output = query_ollama(current_developer_prompt, selected_ollama_model)
                    except Exception as o_err:
                        return f"❌ Gemini API limiti aşıldı ve yerel Ollama da başarısız oldu: {o_err}"
                else:
                    if i < max_retries - 1:
                        print("[CODER] İstek limitine takılındı. 4 saniye beklenip yeniden denenecek...")
                        time.sleep(4)
                        continue
                    else:
                        return f"❌ Gemini API Çağrı Hatası: {e}"
                        
        files = parse_multi_files(code_output)
        if not files:
            previous_errors = "Dosya ayrıştırma hatası: Yazdığın kodda geçerli kod bulunamadı."
            continue

        if "" in files:
            files[filepath] = files.pop("")

        # ── Boş/Placeholder dosya kontrolü ──────────────────────────────
        empty_files = []
        for fname, fcontent in files.items():
            stripped = fcontent.strip()
            # Daha akılı boş dosya tespiti: 200 karakterden kısa + hiç function/class yok = reddedilir
            has_function = "def " in stripped
            has_class = "class " in stripped
            has_import = "import " in stripped or "from " in stripped
            
            is_too_short = len(stripped) < 100  # Threshold'u 50'den 100'e çıkar
            is_stub = any(bad in stripped.lower() for bad in [
                "pass  # ", "todo", "placeholder", "# buraya", 
                "# implement", "# add code", "notimplementederror", "raise notimpl"
            ])
            is_empty_shell = len(stripped) < 200 and not (has_function or has_class or has_import)
            
            if fname.lower() != "requirements.txt" and (is_stub or (is_too_short and is_empty_shell)):
                empty_files.append(fname)

        if empty_files:
            print(f"[CODER] ⚠️ Boş/placeholder dosyalar tespit edildi: {empty_files}. Yeniden üretiliyor...")
            previous_errors = (
                f"Şu dosyaların içeriği boş, eksik veya sadece 'pass/todo/placeholder' ifadesi içeriyor: {empty_files}. "
                f"Bu dosyaların da GERÇEk, ÇALIŞAN Python implementasyonunu yaz. Hiçbir dosyayı boş bırakma!"
            )
            continue
        # ────────────────────────────────────────────────────────────────

        for fname, fcontent in files.items():
            fpath = os.path.join(project_dir, fname)
            # dirname boş olabilir (sadece dosya adı verilmişse), makedirs'i korumaya al
            parent_dir = os.path.dirname(fpath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            # Model bazen içeriğin başına '# FILE: xxx.py' yorumu bırakır → pylint syntax hatası
            # Bu artefakti temizle
            cleaned_content = fcontent
            first_line = fcontent.lstrip().split("\n")[0].strip()
            if first_line.startswith("# FILE:") or first_line.startswith("# file:"):
                cleaned_content = "\n".join(fcontent.lstrip().split("\n")[1:]).lstrip()
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(cleaned_content)
            print(f"[CODER] Dosya kaydedildi: {fpath}")

        # Otomatik formatlama (Ruff)
        print("[CODER] 🧹 Kodlar Ruff ile otomatik formatlanıyor...")
        subprocess.run([venv_python, "-m", "ruff", "format", "."], cwd=project_dir, capture_output=True)

        # Dinamik bağımlılık çözücü (AST ile importları tarama) ve requirements.txt kurulumu
        req_path = os.path.join(project_dir, "requirements.txt")
        if os.path.exists(req_path):
            print("[CODER] 📦 requirements.txt bulundu, kütüphaneler kuruluyor...")
            req_res = subprocess.run([venv_pip, "install", "-r", "requirements.txt"], cwd=project_dir, capture_output=True, text=True)
            if req_res.returncode != 0:
                print(f"[CODER] ⚠️ requirements.txt kurulumunda hata/uyarı: {req_res.stderr}")
        else:
            print("[CODER] 🔍 requirements.txt bulunamadı, kod içi importlar taranıyor...")
            import ast
            std_libs = sys.stdlib_module_names if hasattr(sys, "stdlib_module_names") else set()
            found_imports = set()
            for fname, fcontent in files.items():
                if fname.endswith('.py'):
                    try:
                        tree = ast.parse(fcontent)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for n in node.names:
                                    found_imports.add(n.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    found_imports.add(node.module.split('.')[0])
                    except: pass
            
            to_install = [pkg for pkg in found_imports if pkg not in std_libs and pkg not in ["os", "sys", "time", "json", "re", "math"]]
            if to_install:
                print(f"[CODER] 📦 Tespit edilen eksik paketler kuruluyor: {to_install}")
                subprocess.run([venv_pip, "install"] + to_install, cwd=project_dir, capture_output=True)

        main_run_file = filepath
        if "src/main.py" in files or os.path.exists(os.path.join(project_dir, "src", "main.py")):
            main_run_file = "src/main.py"
        elif "main.py" in files or os.path.exists(os.path.join(project_dir, "main.py")):
            main_run_file = "main.py"
        elif "src/" + filepath in files or os.path.exists(os.path.join(project_dir, "src", filepath)):
            main_run_file = "src/" + filepath

        # --- AŞAMA 3: Statik Güvenlik ve Kalite Analizi (Bandit & Pylint) ---
        print("[CODER] 🔍 Statik kod analizi ve güvenlik taraması yapılıyor...")
        # venv/ dizinini hariç tut — aksi halde pytest/bandit kendi içindeki kodları tarar (false positive)
        bandit_res = subprocess.run(
            [venv_python, "-m", "bandit", "-r", ".", "--exclude", "./venv,./test_project.py"],
            cwd=project_dir, capture_output=True, text=True
        )
        pylint_res = subprocess.run(
            [venv_python, "-m", "pylint", "--errors-only", main_run_file],
            cwd=project_dir, capture_output=True, text=True
        )
        
        static_errors = ""
        # Sadece HIGH severity bandit bulgularını engelle (Medium/Low venv'den gelebilir)
        if bandit_res.returncode != 0 and "No module named bandit" in (bandit_res.stderr or ""):
            print("[CODER] ⚠️ bandit sanal ortamda bulunamadı, güvenlik taraması atlanıyor...")
        elif "Severity: High" in bandit_res.stdout:
            bandit_issues = [
                line for line in bandit_res.stdout.split('\n')
                if ("Severity:" in line or "Location:" in line) and "venv" not in line
            ]
            if bandit_issues:
                static_errors += f"\n[Bandit Yüksek Güvenlik Uyarısı]:\n" + "\n".join(bandit_issues[:10])
            
        if pylint_res.returncode != 0 and "No module named pylint" in (pylint_res.stderr or ""):
            print("[CODER] ⚠️ pylint sanal ortamda bulunamadı, statik analiz atlanıyor...")
        elif pylint_res.returncode != 0 and pylint_res.stdout.strip():
            # 'Unable to import' uyarıları eksik modülden gelir, import hatasıyla aynı şey —
            # bunları aşama 4'teki otomatik pip kurulumu zaten halleder, statik engel koyma
            pylint_out = pylint_res.stdout
            critical_pylint = [l for l in pylint_out.splitlines()
                               if " E0" in l and "E0401" not in l]  # E0401 = import-error, skip
            if critical_pylint:
                static_errors += f"\n[Pylint Sözdizimi/Derleme Hatası]:\n" + "\n".join(critical_pylint)
            
        if static_errors:
            print(f"[CODER] ❌ Statik analizde hatalar bulundu. Düzeltme başlatılıyor...")
            previous_errors = f"Yazdığın kod güvenlik veya kalite taramasından geçemedi:{static_errors}"
            continue

        # --- AŞAMA 4: Kod Çalıştırma (Sandbox venv) ---
        print(f"[CODER] Kod çalıştırılıyor...")
        returncode = -1
        stdout = ""
        stderr = ""
        
        try:
            result = subprocess.run(
                [venv_python, main_run_file],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=60  # Timeout'u 30'dan 60 saniyeye çıkar
            )
            returncode = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired as e:
            stderr = f"Zaman aşımı (Timeout): Kod 60 saniye içinde çalışmayı bitirmedi veya sonsuz döngüye girdi. Ek bilgi: {e}"
        except Exception as e:
            stderr = f"Bilinmeyen hata oluştu: {e}"
            
        # Otomatik Kütüphane Kurulumu (Pip Sandbox Installer)
        missing_module = None
        match = re.search(r"ModuleNotFoundError:\s*No\s*module\s*named\s*['\"](.*?)['\"]", stderr)
        if not match:
            match = re.search(r"ImportError:\s*No\s*module\s*named\s*(.*)", stderr)
        if match:
            missing_module = match.group(1).split('.')[0].strip()
            
        if missing_module:
            print(f"[CODER] 📦 Eksik kütüphane tespit edildi: {missing_module}. Sanal ortama kuruluyor...")
            install_res = subprocess.run(
                [venv_pip, "install", missing_module],
                capture_output=True,
                text=True
            )
            if install_res.returncode == 0:
                print(f"[CODER] ✅ {missing_module} başarıyla kuruldu. Kod tekrar çalıştırılıyor...")
                try:
                    result = subprocess.run(
                        [venv_python, main_run_file],
                        cwd=project_dir,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    returncode = result.returncode
                    stdout = result.stdout
                    stderr = result.stderr
                except Exception as e:
                    stderr = f"Tekrar çalıştırma hatası: {e}"
            else:
                stderr += f"\n[JARVIS]: '{missing_module}' otomatik kurulmaya çalışıldı fakat başarısız oldu: {install_res.stderr}"

        # --- AŞAMA 5: Çift Ajanlı Test Koşturması (pytest) ---
        if returncode == 0:
            print(f"\n🛡️ Testçi Ajan (Tester) çalışıyor...")
            project_files_str = ""
            for fname, fcontent in files.items():
                project_files_str += f"Dosya: {fname}\n```python\n{fcontent}\n```\n\n"
                
            test_prompt = (
                f"Sen F.R.I.D.A.Y.'in otonom Testçi Ajanı'sın.\n"
                f"Geliştirici Ajan şu dosyaları oluşturdu:\n\n{project_files_str}"
                f"Lütfen bu dosyaların mantıksal olarak doğru çalışıp çalışmadığını sınayacak pytest uyumlu bir `test_project.py` dosyası yaz.\n"
                f"Sadece test kodunu döndür. Markdown (```python) kullanma, sadece saf python kodu olsun.\n"
                f"Testler mantıklı assertions (savlar) içermelidir."
            )
            
            test_code = ""
            if use_ollama and selected_ollama_model:
                try:
                    test_code = query_ollama(test_prompt, selected_ollama_model, stream=False)
                except Exception:
                    pass
            elif api_key:
                # Test fazında da client hazır olmalı
                if client is None:
                    try:
                        client = genai.Client(api_key=api_key)
                    except Exception:
                        pass
                if client:
                    try:
                        res = client.models.generate_content(
                            model="models/gemini-2.5-flash",
                            contents=[types.Part.from_text(text=test_prompt)]
                        )
                        test_code = str(getattr(res, "text", "") or "").strip()
                    except Exception:
                        pass
                    
            if test_code:
                if test_code.startswith("```python"):
                    test_code = test_code[9:]
                elif test_code.startswith("```"):
                    test_code = test_code[3:]
                if test_code.endswith("```"):
                    test_code = test_code[:-3]
                test_code = test_code.strip()
                
                test_filepath = os.path.join(project_dir, "test_project.py")
                with open(test_filepath, "w", encoding="utf-8") as f:
                    f.write(test_code)
                print(f"[CODER] Test dosyası kaydedildi: {test_filepath}")
                
                print("[CODER] Testler (pytest) koşturuluyor...")
                test_res = subprocess.run(
                    [venv_python, "-m", "pytest", "test_project.py", "-v"],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=40
                )
                
                if test_res.returncode == 0:
                    print(f"[CODER] ✅ Tüm testler başarıyla geçti!")
                    # Git checkout branch & gh PR create
                    commit_msg = f"Auto-Coder: {task[:40]}"
                    try:
                        git_res = create_branch_and_pr(project_dir, project_name, commit_msg)
                    except Exception as git_err:
                        git_res = f"GitHub işlemi sırasında uyarı (devam edildi): {str(git_err)[:100]}"
                        
                    files_summary = "\n".join([f"- {fn}" for fn in files.keys()])
                    return (f"✅ Proje başarıyla kodlandı, testleri geçti ve GitHub PR oluşturuldu!\n"
                            f"Klasör: {project_dir}\n"
                            f"[Motor: {active_engine_name}]\n"
                            f"Dosyalar:\n{files_summary}\n\n"
                            f"GitHub İşlemi:\n{git_res}\n\n"
                            f"Test Sonuçları (pytest):\n{test_res.stdout}")
                else:
                    print(f"[CODER] ❌ Bazı testler başarısız oldu. Düzeltme başlatılıyor...")
                    previous_errors = f"Yazılan testler başarısız oldu:\n{test_res.stdout}\n{test_res.stderr}"
            else:
                commit_msg = f"Auto-Coder: {task[:40]}"
                try:
                    git_res = create_branch_and_pr(project_dir, project_name, commit_msg)
                except Exception as git_err:
                    git_res = f"GitHub işlemi sırasında uyarı (devam edildi): {str(git_err)[:100]}"
                return (f"✅ Proje başarıyla kodlandı, çalıştırıldı ve GitHub PR oluşturuldu!\n"
                        f"Klasör: {project_dir}\n"
                        f"[Motor: {active_engine_name}]\n"
                        f"GitHub İşlemi:\n{git_res}\n\n"
                        f"Çıktı:\n{stdout}")
        else:
            previous_errors = f"Kod çalışırken hata verdi:\n{stderr}"
            
    return f"❌ {max_retries} denemede çalışan kod veya test başarısı elde edilemedi. Son hata: {previous_errors}"

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="F.R.I.D.A.Y. Otonom Kod Geliştirici CLI")
    parser.add_argument("--task", type=str, required=True, help="Yapılması istenen kodlama görevi.")
    parser.add_argument("--filename", type=str, default="generated_project.py", help="Kodun yazılacağı dosya adı.")
    parser.add_argument("--retries", type=int, default=3, help="Hata durumunda maksimum deneme sayısı.")
    
    args = parser.parse_args()
    
    print(f"Otonom Coder CLI Başlatıldı.")
    print(f"Görev: {args.task}")
    print(f"Dosya: {args.filename}")
    print(f"Deneme Sayısı: {args.retries}")
    print("-" * 50)
    
    result = generate_and_run_code(args.task, filepath=args.filename, max_retries=args.retries)
    print("\n" + "=" * 50)
    print(result)
