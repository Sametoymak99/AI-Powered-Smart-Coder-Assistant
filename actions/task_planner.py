"""
Çok Adımlı Görev Planlayıcı — F.R.I.D.A.Y
Karmaşık görevleri adımlara böler ve sırayla çalıştırır.
"""

import json
import datetime
from typing import Optional, Callable

# Aktif plan durumu (tek plan aynı anda)
_active_plan: Optional[dict] = None
_progress_callback: Optional[Callable[[str], None]] = None


def set_progress_callback(cb: Callable[[str], None]):
    """UI log yazıcısını bağlar."""
    global _progress_callback
    _progress_callback = cb


def _log(msg: str):
    if _progress_callback:
        _progress_callback(msg)
    print(f"[TaskPlanner] {msg}")


def create_plan(goal: str, steps: list) -> str:
    """
    Hedef ve adım listesiyle yeni bir plan oluşturur.
    steps: [{"id":1, "description":"...", "tool":"...", "action":"...", "args":{...}}, ...]
    """
    global _active_plan

    if not goal:
        return "Plan hedefi boş olamaz."
    if not steps:
        return "Plan adımları boş olamaz."

    _active_plan = {
        "goal": goal,
        "created_at": datetime.datetime.now().isoformat(),
        "status": "ready",          # ready | running | done | cancelled | error
        "current_step": 0,
        "steps": []
    }

    for i, step in enumerate(steps):
        _active_plan["steps"].append({
            "id": i + 1,
            "description": step.get("description", f"Adım {i+1}"),
            "tool": step.get("tool", "shell_run"),
            "action": step.get("action", ""),
            "args": step.get("args", {}),
            "status": "pending",    # pending | running | done | error | skipped
            "result": None,
        })

    lines = [
        f"📋 PLAN OLUŞTURULDU: {goal}",
        f"{'─'*55}",
    ]
    for step in _active_plan["steps"]:
        lines.append(f"  {step['id']}. {step['description']}")
    lines.append(f"{'─'*55}")
    lines.append(f"Toplam {len(_active_plan['steps'])} adım. Çalıştırmak için onay verin.")

    return "\n".join(lines)


def get_active_plan() -> str:
    """Mevcut aktif planın durumunu döndürür."""
    if not _active_plan:
        return "Aktif plan yok."

    goal = _active_plan["goal"]
    status_map = {
        "ready": "⏳ Hazır (bekliyor)",
        "running": "▶️ Çalışıyor",
        "done": "✅ Tamamlandı",
        "cancelled": "❌ İptal edildi",
        "error": "⚠️ Hata oluştu",
    }
    status_str = status_map.get(_active_plan["status"], _active_plan["status"])

    lines = [
        f"📋 PLAN: {goal}",
        f"Durum: {status_str}",
        f"{'─'*55}",
    ]

    step_icons = {
        "pending": "⬜",
        "running": "▶️",
        "done": "✅",
        "error": "❌",
        "skipped": "⏭️",
    }

    for step in _active_plan["steps"]:
        icon = step_icons.get(step["status"], "❓")
        result_preview = ""
        if step["result"]:
            r = str(step["result"])[:60]
            result_preview = f" → {r}..."
        lines.append(f"  {icon} {step['id']}. {step['description']}{result_preview}")

    return "\n".join(lines)


def cancel_plan() -> str:
    """Aktif planı iptal eder."""
    global _active_plan
    if not _active_plan:
        return "İptal edilecek aktif plan yok."

    goal = _active_plan["goal"]
    _active_plan["status"] = "cancelled"

    for step in _active_plan["steps"]:
        if step["status"] == "pending":
            step["status"] = "skipped"

    return f"❌ Plan iptal edildi: {goal}"


def execute_plan(tool_executor: Callable) -> str:
    """
    Aktif planı adım adım çalıştırır.
    tool_executor: (tool_name, action, args) -> str dönen senkron fonksiyon.
    """
    global _active_plan

    if not _active_plan:
        return "Çalıştırılacak plan yok. Önce create_task_plan kullanın."

    if _active_plan["status"] == "cancelled":
        return "Plan iptal edilmiş. Yeni plan oluşturun."

    if _active_plan["status"] == "done":
        return "Plan zaten tamamlandı."

    _active_plan["status"] = "running"
    goal = _active_plan["goal"]
    steps = _active_plan["steps"]
    total = len(steps)

    _log(f"🚀 Plan başlatıldı: {goal} ({total} adım)")

    errors = []
    completed = 0

    for step in steps:
        if step["status"] in ("done", "skipped"):
            continue

        if _active_plan["status"] == "cancelled":
            step["status"] = "skipped"
            continue

        step["status"] = "running"
        _log(f"  ▶️ Adım {step['id']}/{total}: {step['description']}")

        try:
            result = tool_executor(
                step["tool"],
                step.get("action", ""),
                step.get("args", {})
            )
            step["result"] = result
            step["status"] = "done"
            completed += 1

            # Kısa sonuç logu
            preview = str(result)[:100].replace("\n", " ")
            _log(f"  ✅ Adım {step['id']} tamamlandı: {preview}")

        except Exception as e:
            step["result"] = str(e)
            step["status"] = "error"
            errors.append(f"Adım {step['id']}: {e}")
            _log(f"  ❌ Adım {step['id']} hatası: {e}")

    # Özet
    if _active_plan["status"] != "cancelled":
        _active_plan["status"] = "done" if not errors else "error"

    lines = [
        f"📋 PLAN TAMAMLANDI: {goal}",
        f"{'─'*55}",
        f"✅ Başarılı: {completed}/{total} adım",
    ]

    if errors:
        lines.append(f"❌ Hatalar ({len(errors)}):")
        for err in errors:
            lines.append(f"   • {err}")

    # Her adımın sonucu
    lines.append(f"\n{'─'*55}\nDetaylı Sonuçlar:")
    for step in steps:
        icon = "✅" if step["status"] == "done" else ("❌" if step["status"] == "error" else "⏭️")
        lines.append(f"\n{icon} {step['id']}. {step['description']}")
        if step["result"]:
            result_text = str(step["result"])
            # İlk 300 karakter
            if len(result_text) > 300:
                result_text = result_text[:300] + "..."
            for line in result_text.splitlines():
                lines.append(f"   {line}")

    return "\n".join(lines)
