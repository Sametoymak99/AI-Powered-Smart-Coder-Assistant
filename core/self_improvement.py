import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("SelfImprovement")

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "memory" / "improvement_log.json"

class SelfImprovement:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SelfImprovement, cls).__new__(cls)
            cls._instance._init_improvement()
        return cls._instance

    def _init_improvement(self):
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not LOG_FILE.exists():
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"failures": [], "successes": [], "metrics": {}}, f, indent=2)

    def log_failure(self, tool_name: str, error: str, context: str = "") -> None:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["failures"].append({
                "timestamp": int(time.time()),
                "tool": tool_name,
                "error": error,
                "context": context
            })
            
            # Keep log size reasonable
            if len(data["failures"]) > 200:
                data["failures"].pop(0)
                
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Self-improvement logged failure for tool {tool_name}.")
        except Exception as e:
            logger.error(f"Error logging failure: {e}")

    def log_success(self, tool_name: str, duration_ms: int) -> None:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data["successes"].append({
                "timestamp": int(time.time()),
                "tool": tool_name,
                "duration_ms": duration_ms
            })
            
            if len(data["successes"]) > 200:
                data["successes"].pop(0)
                
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error logging success: {e}")

    def get_failure_stats(self) -> Dict[str, Any]:
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return {}
            
        stats = {}
        for fail in data.get("failures", []):
            tool = fail.get("tool", "unknown")
            if tool not in stats:
                stats[tool] = 0
            stats[tool] += 1
        return stats

    def generate_weekly_report(self) -> str:
        stats = self.get_failure_stats()
        if not stats:
            return "Sistem performans verileri henüz toplanmadı. Tüm sistemler kararlı çalışıyor."
            
        lines = ["# 🧠 F.R.I.D.A.Y. NEXUS Self-Improvement Haftalık Raporu\n"]
        lines.append("Son dönemde gerçekleşen hata analizleri ve düzeltme önerileri:\n")
        lines.append("| Araç (Tool) | Hata Sayısı | Çözüm/Öneri |")
        lines.append("|---|---|---|")
        
        for tool, count in stats.items():
            suggestion = "Bilinmeyen hata deseni. Kütüphane bağımlılıklarını veya API anahtarlarını kontrol edin."
            if "arduino" in tool.lower():
                suggestion = "Port veya kablo bağlantısını kontrol edin, Arduino kartının yüklendiğinden emin olun."
            elif "whatsapp" in tool.lower():
                suggestion = "Tarayıcı oturumunun açık olduğundan veya telefonun internet bağlantısının stabil olduğundan emin olun."
            elif "email" in tool.lower():
                suggestion = "SMTP ayarlarını ve yetkilendirme şifresini (App Password) doğrulayın."
            elif "coder" in tool.lower():
                suggestion = "Sanal ortam (venv) kurulumunda veya paket indirme aşamasında hata olabilir, internet bağlantınızı kontrol edin."
                
            lines.append(f"| {tool} | {count} | {suggestion} |")
            
        return "\n".join(lines)

self_improver = SelfImprovement()
