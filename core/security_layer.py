import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("SecurityLayer")

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_FILE = BASE_DIR / "memory" / "audit_log.jsonl"

class SecurityLayer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityLayer, cls).__new__(cls)
            cls._instance._init_security()
        return cls._instance

    def _init_security(self):
        self.DANGEROUS_PATTERNS = [
            "rm -rf", "format ", "del /f", "del /s", "net user", "reg delete", 
            "taskkill", "shutdown", "mkfs", "dd if=", "chmod 777", "chown "
        ]
        
        self.DANGEROUS_PYTHON = [
            "eval(", "exec(", "__import__", "os.system", "subprocess.Popen", 
            "shutil.rmtree", "os.remove"
        ]
        
        self.admin_mode = False
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def check_shell_command(self, cmd: str) -> Tuple[bool, str]:
        cmd_clean = cmd.strip().lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in cmd_clean:
                if not self.admin_mode:
                    return False, f"Engellendi: Tehlikeli shell komut deseni tespit edildi ('{pattern}'). Lütfen admin modunu açın."
        return True, "Safe"

    def check_python_code(self, code: str) -> Tuple[bool, List[str]]:
        warnings = []
        for pattern in self.DANGEROUS_PYTHON:
            if pattern in code:
                warnings.append(f"Tehlikeli Python deseni: '{pattern}'")
                
        if warnings and not self.admin_mode:
            return False, warnings
        return True, warnings

    def log_audit(self, action: str, tool: str, args: Dict[str, Any], result: str, risk_level: str = "low"):
        log_entry = {
            "timestamp": int(time.time()) if 'time' in globals() else 0,
            "action": action,
            "tool": tool,
            "args": str(args),
            "result": result[:200] + "..." if len(result) > 200 else result,
            "risk_level": risk_level
        }
        
        try:
            with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")

    def get_audit_log(self, last_n: int = 50) -> List[Dict[str, Any]]:
        entries = []
        if AUDIT_FILE.exists():
            try:
                with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
            except Exception as e:
                logger.error(f"Error reading audit file: {e}")
        return entries[-last_n:]

security_layer = SecurityLayer()
