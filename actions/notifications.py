"""
Windows Bildirim & WhatsApp Okuyucu -- winsdk'siz surum
F.R.I.D.A.Y -- PowerShell + SQLite yontemiyle bildirim okuma

Windows 10/11, bildirimleri su SQLite veritabaninda tutar:
  LOCALAPPDATA/Microsoft/Windows/Notifications/wpndatabase.db
"""

import os
import sqlite3
import subprocess
import json
import datetime
from pathlib import Path
from typing import Optional


# ── Windows Bildirim Veritabanı Yolu ────────────────────────────────────────
WPN_DB = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Notifications" / "wpndatabase.db"


def _read_wpn_database(filter_app: Optional[str] = None, limit: int = 30) -> list[dict]:
    """
    Windows bildirim veritabanından (wpndatabase.db) bildirimleri okur.
    Dönüş: [{"app": str, "title": str, "body": str, "time": str}, ...]
    """
    if not WPN_DB.exists():
        return []

    # DB dosyası kilitli olabilir — önce kopyala
    import shutil, tempfile
    tmp = Path(tempfile.mktemp(suffix=".db"))
    try:
        shutil.copy2(WPN_DB, tmp)
    except PermissionError:
        return []

    results = []
    try:
        conn = sqlite3.connect(str(tmp))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Tablo yapısını kontrol et
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        if "Notification" in tables:
            query = """
                SELECT
                    h.PrimaryId   AS app_id,
                    h.AppDisplayName AS app_name,
                    n.Payload     AS payload,
                    n.ArrivalTime AS arrival_time
                FROM Notification n
                LEFT JOIN NotificationHandler h ON n.HandlerId = h.RecordId
                ORDER BY n.ArrivalTime DESC
                LIMIT ?
            """
            rows = cur.execute(query, (limit,)).fetchall()

            for row in rows:
                app_name = row["app_name"] or row["app_id"] or "Sistem"

                # Filtre
                if filter_app and filter_app.lower() not in app_name.lower():
                    continue

                # Payload XML'den title ve body çek
                payload = row["payload"] or ""
                title, body = _parse_toast_payload(payload)

                # Zaman
                arrival = row["arrival_time"]
                time_str = _filetime_to_str(arrival) if arrival else "—"

                if title or body:
                    results.append({
                        "app": app_name,
                        "title": title,
                        "body": body,
                        "time": time_str,
                    })

        conn.close()
    except Exception:
        pass
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass

    return results


def _parse_toast_payload(xml_str: str) -> tuple[str, str]:
    """Toast XML payload'ından başlık ve gövde metnini çıkarır."""
    if not xml_str:
        return "", ""

    title = ""
    body_parts = []

    try:
        import re
        # <text> etiketleri arasındaki metni çek
        texts = re.findall(r"<text[^>]*>([^<]+)</text>", xml_str, re.IGNORECASE)
        if texts:
            title = texts[0].strip()
            body_parts = [t.strip() for t in texts[1:] if t.strip()]
    except Exception:
        pass

    return title, " | ".join(body_parts)


def _filetime_to_str(filetime: int) -> str:
    """Windows FILETIME (100-nanosecond intervals since 1601) → okunabilir tarih."""
    try:
        # Windows FILETIME → Unix timestamp
        unix_ts = (int(filetime) - 116444736000000000) / 10_000_000
        dt = datetime.datetime.fromtimestamp(unix_ts)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return "—"


def _read_via_powershell() -> list[dict]:
    """
    PowerShell üzerinden Windows Action Center bildirimlerini okur.
    BurntToast modülü mevcutsa onu kullanır, yoksa process listesinden bilgi toplar.
    """
    # Yöntem 1: Windows 10/11 Action Center history PowerShell komutu
    ps_script = r"""
try {
    $source = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    $history = [Windows.UI.Notifications.ToastNotificationManager]::History
    $items = $history.GetHistory()
    $results = @()
    foreach ($item in $items) {
        $xml = $item.Content.GetXml()
        $results += [PSCustomObject]@{
            AppId = $item.AppId
            Xml   = $xml
        }
    }
    $results | ConvertTo-Json -Depth 3
} catch {
    "ERROR: " + $_.Exception.Message
}
"""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            text=True, timeout=10, stderr=subprocess.DEVNULL
        ).strip()

        if out.startswith("ERROR") or not out or out == "null":
            return []

        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]

        results = []
        for item in data:
            app_id = item.get("AppId", "Sistem")
            xml_str = item.get("Xml", "")
            title, body = _parse_toast_payload(xml_str)
            if title or body:
                results.append({"app": app_id, "title": title, "body": body, "time": "—"})
        return results

    except Exception:
        return []


# ── Ana Fonksiyonlar ─────────────────────────────────────────────────────────

def read_notifications(filter_app: Optional[str] = None) -> str:
    """
    Windows bildirimlerini okur.
    Önce wpndatabase.db yöntemini dener, başarısız olursa PowerShell WinRT yöntemine geçer.
    """
    results = _read_wpn_database(filter_app=filter_app, limit=20)

    if not results:
        results = _read_via_powershell()
        if filter_app:
            results = [r for r in results if filter_app.lower() in r.get("app", "").lower()]

    if not results:
        return "📭 Şu an okunmamış bildiriminiz yok (veya erişim izni yok)."

    lines = [f"🔔 Bildirimler:\n{'─'*50}"]
    for r in results[:15]:
        app = r.get("app", "?")
        title = r.get("title", "")
        body = r.get("body", "")
        time_str = r.get("time", "")
        content = title
        if body:
            content = f"{title} — {body}" if title else body
        time_part = f" [{time_str}]" if time_str and time_str != "—" else ""
        lines.append(f"  • [{app}]{time_part} {content}")

    return "\n".join(lines)


def read_whatsapp_messages(count: int = 10) -> str:
    """
    WhatsApp Desktop bildirimleri için filtrelenmiş okuma.
    Hem wpndatabase.db hem PowerShell yöntemini dener.
    """
    # Önce DB yöntemi
    results = _read_wpn_database(filter_app="WhatsApp", limit=count + 5)

    # DB boşsa PowerShell
    if not results:
        results = _read_via_powershell()
        results = [r for r in results if "whatsapp" in r.get("app", "").lower()]

    # Hâlâ boşsa: WhatsApp açık mı kontrol et
    if not results:
        try:
            ps_check = (
                'Get-Process | Where-Object {$_.MainWindowTitle -like "*WhatsApp*"} | '
                'Select-Object -First 1 -ExpandProperty MainWindowTitle'
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_check],
                text=True, timeout=5, stderr=subprocess.DEVNULL
            ).strip()

            if out:
                return (
                    "📱 WhatsApp açık görünüyor ancak bildirim veritabanında mesaj bulunamadı.\n"
                    "Not: WhatsApp Desktop'ın bildirimlerinin Windows Bildirim Merkezi'nde görünmesi için "
                    "Windows Ayarları → Sistem → Bildirimler → WhatsApp → 'Bildirim Merkezi'nde göster' seçeneğini açın."
                )
            else:
                return (
                    "📱 WhatsApp Desktop kapalı veya bildirim veritabanında WhatsApp mesajı yok.\n"
                    "İpucu: WhatsApp Desktop uygulamasını açık tutun."
                )
        except Exception:
            pass

        return "📭 WhatsApp bildirimi bulunamadı."

    lines = [f"📱 WhatsApp Mesajları ({len(results)}):\n{'─'*50}"]
    for r in results[:count]:
        title = r.get("title", "")
        body = r.get("body", "")
        time_str = r.get("time", "")
        content = body or title
        time_part = f" [{time_str}]" if time_str and time_str != "—" else ""
        lines.append(f"  • {title}{time_part}: {body}" if title and body else f"  • {content}{time_part}")

    return "\n".join(lines)


def get_notification_summary() -> str:
    """Tüm bildirimleri uygulamaya göre gruplar."""
    results = _read_wpn_database(limit=50)
    if not results:
        results = _read_via_powershell()

    if not results:
        return "📭 Bildirim bulunamadı."

    # Uygulamaya göre grupla
    groups: dict[str, list] = {}
    for r in results:
        app = r.get("app", "Sistem")
        groups.setdefault(app, []).append(r)

    lines = [f"🔔 Bildirim Özeti — {len(results)} bildirim\n{'─'*50}"]
    for app, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        lines.append(f"\n📱 {app} ({len(items)} bildirim):")
        for item in items[:3]:
            title = item.get("title", "")
            body = item.get("body", "")
            time_str = item.get("time", "")
            content = f"{title} — {body}" if title and body else (title or body)
            time_part = f" [{time_str}]" if time_str and time_str != "—" else ""
            lines.append(f"   • {content}{time_part}")
        if len(items) > 3:
            lines.append(f"   ... ve {len(items)-3} bildirim daha")

    return "\n".join(lines)
