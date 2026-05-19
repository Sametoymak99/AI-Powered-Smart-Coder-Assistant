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

def create_and_push_new_project(project_dir: str, project_name: str, commit_msg: str) -> str:
    """Belirtilen dizini git reposu yapar, GitHub'da repo oluşturur ve pushlar."""
    try:
        if not os.path.exists(os.path.join(project_dir, ".git")):
            subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
            
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=project_dir, capture_output=True)
        
        res = subprocess.run(["git", "remote", "-v"], cwd=project_dir, capture_output=True, text=True)
        if "origin" not in res.stdout:
            gh_res = subprocess.run(
                ["gh", "repo", "create", project_name, "--public", "--source=.", "--remote=origin", "--push"],
                cwd=project_dir, capture_output=True, text=True
            )
            if gh_res.returncode != 0:
                return f"GitHub repo oluşturma hatası (gh CLI):\n{gh_res.stderr}"
            return f"Yeni repo oluşturuldu ve kodlar yüklendi:\n{gh_res.stdout}"
        else:
            push_res = subprocess.run(["git", "push", "-u", "origin", "master"], cwd=project_dir, capture_output=True, text=True)
            if push_res.returncode != 0:
                push_res = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=project_dir, capture_output=True, text=True)
            return f"Değişiklikler GitHub'a yüklendi.\n{push_res.stdout}\n{push_res.stderr}"
            
    except FileNotFoundError:
        return "Hata: 'git' veya 'gh' bulunamadı. Lütfen yüklü olduklarından emin olun."
    except Exception as e:
        return f"Beklenmeyen bir hata oluştu: {str(e)}"

def create_branch_and_pr(project_dir: str, project_name: str, commit_msg: str) -> str:
    """Yeni bir git dalı (branch) açar, dosyaları yükler ve Pull Request oluşturur."""
    import time
    import os
    try:
        if not os.path.exists(os.path.join(project_dir, ".git")):
            # Eğer git reposu değilse init yap
            subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
            
        # 1. Branch adı oluştur: friday/auto-<project_name>-<timestamp>
        timestamp = int(time.time())
        branch_name = f"friday/auto-{project_name.lower()}-{timestamp}"
        
        # 2. git checkout -b branch_name
        checkout_res = subprocess.run(["git", "checkout", "-b", branch_name], cwd=project_dir, capture_output=True, text=True)
        if checkout_res.returncode != 0:
            # Eğer branch zaten varsa geçiş yap
            subprocess.run(["git", "checkout", branch_name], cwd=project_dir, capture_output=True)
            
        # 3. git add . ve git commit
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=project_dir, capture_output=True)
        
        # 4. GitHub remote kontrol et
        res = subprocess.run(["git", "remote", "-v"], cwd=project_dir, capture_output=True, text=True)
        if "origin" not in res.stdout:
            # gh CLI ile yeni repo oluştur
            gh_res = subprocess.run(
                ["gh", "repo", "create", project_name, "--public", "--source=.", "--remote=origin", "--push"],
                cwd=project_dir, capture_output=True, text=True
            )
            if gh_res.returncode != 0:
                return f"GitHub repo oluşturma hatası:\n{gh_res.stderr}"
        else:
            # Push branch
            push_res = subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=project_dir, capture_output=True, text=True)
            if push_res.returncode != 0:
                return f"Git branch push hatası:\n{push_res.stderr}"
                
        # 5. gh pr create
        pr_res = subprocess.run(
            ["gh", "pr", "create", "--title", f"Otonom Coder: {project_name} Geliştirmesi", "--body", f"F.R.I.D.A.Y. tarafından otomatik oluşturulan geliştirme.\nCommit: {commit_msg}", "--base", "main"],
            cwd=project_dir, capture_output=True, text=True
        )
        
        pr_status = ""
        if pr_res.returncode == 0:
            pr_status = f"✅ PR Başarıyla Açıldı!\nLink: {pr_res.stdout.strip()}"
        else:
            # Eğer base 'main' değil de 'master' ise tekrar dene
            pr_res_master = subprocess.run(
                ["gh", "pr", "create", "--title", f"Otonom Coder: {project_name} Geliştirmesi", "--body", f"F.R.I.D.A.Y. tarafından otomatik oluşturulan geliştirme.\nCommit: {commit_msg}", "--base", "master"],
                cwd=project_dir, capture_output=True, text=True
            )
            if pr_res_master.returncode == 0:
                pr_status = f"✅ PR Başarıyla Açıldı!\nLink: {pr_res_master.stdout.strip()}"
            else:
                pr_status = f"⚠️ Dal pushlandı fakat PR oluşturulamadı. Hata: {pr_res_master.stderr.strip()}"
                
        return f"Dallar güncellendi: {branch_name}\n{pr_status}"
        
    except FileNotFoundError:
        return "Hata: 'git' veya 'gh' bulunamadı. Lütfen yüklü olduklarından emin olun."
    except Exception as e:
        return f"Beklenmeyen bir hata oluştu: {str(e)}"

