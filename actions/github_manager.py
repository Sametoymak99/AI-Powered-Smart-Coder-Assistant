import subprocess
import os

def push_to_github(commit_message: str = "Jarvis tarafından otomatik güncellendi") -> str:
    """Mevcut projeyi GitHub'a commit eder ve pushlar."""
    try:
        # 1. git add .
        add_process = subprocess.run(["git", "add", "."], capture_output=True, text=True)
        if add_process.returncode != 0:
            return f"Git add hatası:\n{add_process.stderr}"
        
        # 2. git commit -m
        commit_process = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True)
        # Commit hatası (örneğin değişen dosya yoksa) çok önemli değil, yine de push'u deneriz
        
        # 3. git push
        push_process = subprocess.run(["git", "push"], capture_output=True, text=True)
        if push_process.returncode != 0:
            # Eğer upstream set edilmemişse (ilk push ise) hata verebilir.
            if "upstream" in push_process.stderr or "set-upstream" in push_process.stderr:
                return "Hata: GitHub'a (remote repo) bağlantı tam kurulmamış veya ilk push işlemi (upstream ayarlanmamış). Lütfen terminalden bir kez 'git push -u origin main' yapın."
            return f"Git push hatası:\n{push_process.stderr}"
        
        return f"Proje başarıyla GitHub'a yüklendi (Push edildi).\n{push_process.stdout}"
        
    except FileNotFoundError:
        return "Hata: Sistemde 'git' komutu bulunamadı. Lütfen Git'in kurulu olduğundan emin olun."
    except Exception as e:
        return f"Beklenmeyen bir hata oluştu: {str(e)}"
