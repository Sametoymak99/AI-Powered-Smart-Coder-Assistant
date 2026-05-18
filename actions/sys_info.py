"""
Sistem Bilgisi — Windows uyumlu
F.R.I.D.A.Y için pil, CPU, RAM, disk, saat, ağ bilgisi
"""

import subprocess
import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def sys_info(query: str) -> str:
    query = query.lower().strip()

    results = []

    if query in ("battery", "pil", "şarj", "all"):
        results.append(_battery())

    if query in ("cpu", "işlemci", "all"):
        results.append(_cpu())

    if query in ("ram", "bellek", "memory", "all"):
        results.append(_ram())

    if query in ("disk", "depolama", "all"):
        results.append(_disk())

    if query in ("time", "saat", "zaman", "all"):
        now = datetime.datetime.now()
        results.append(f"Saat: {now.strftime('%H:%M:%S')}")

    if query in ("date", "tarih", "all"):
        now = datetime.datetime.now()
        results.append(f"Tarih: {now.strftime('%d %B %Y, %A')}")

    if query in ("network", "ağ", "wifi", "internet", "all"):
        results.append(_network())

    if query in ("uptime", "çalışma süresi", "all"):
        results.append(_uptime())

    if query in ("processes", "prosesler", "süreçler"):
        results.append(_top_processes())

    if not results:
        results.append(
            f"Bilinmeyen sorgu: '{query}'. "
            "Geçerli sorgular: battery | cpu | ram | disk | time | date | network | uptime | all"
        )

    return "\n".join(r for r in results if r)


def _battery() -> str:
    if HAS_PSUTIL:
        bat = psutil.sensors_battery()
        if bat:
            status = "Şarj oluyor 🔌" if bat.power_plugged else "Pilde 🔋"
            pct = bat.percent
            # Kalan süre
            if bat.secsleft and bat.secsleft > 0 and not bat.power_plugged:
                h = int(bat.secsleft // 3600)
                m = int((bat.secsleft % 3600) // 60)
                time_str = f" — Kalan: {h}s {m}dk"
            else:
                time_str = ""
            return f"Pil: %{pct:.0f} — {status}{time_str}"
        return "Pil bilgisi bulunamadı (masaüstü bilgisayar olabilir)."
    # Fallback: PowerShell
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_Battery).EstimatedChargeRemaining"],
            text=True, timeout=5, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            return f"Pil: %{out}"
    except Exception:
        pass
    return "Pil bilgisi alınamadı."


def _cpu() -> str:
    if HAS_PSUTIL:
        usage = psutil.cpu_percent(interval=0.5)
        count_logical = psutil.cpu_count(logical=True)
        count_physical = psutil.cpu_count(logical=False) or count_logical
        freq = psutil.cpu_freq()
        freq_str = f", {freq.current:.0f} MHz" if freq else ""
        return (
            f"CPU: %{usage:.1f} kullanım — "
            f"{count_physical} fiziksel / {count_logical} mantıksal çekirdek{freq_str}"
        )
    # PowerShell fallback
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-WmiObject Win32_Processor | Select-Object -ExpandProperty LoadPercentage"],
            text=True, timeout=8, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            return f"CPU: %{out} kullanım"
    except Exception:
        pass
    return "CPU bilgisi alınamadı."


def _ram() -> str:
    if HAS_PSUTIL:
        vm = psutil.virtual_memory()
        total = vm.total / (1024**3)
        used  = vm.used  / (1024**3)
        pct   = vm.percent
        return f"RAM: {used:.1f} GB / {total:.1f} GB kullanımda (%{pct:.0f})"
    # PowerShell fallback
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory"],
            text=True, timeout=5, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            total_gb = int(out) / (1024**3)
            return f"RAM: Toplam {total_gb:.1f} GB (kullanım alınamadı)"
    except Exception:
        pass
    return "RAM bilgisi alınamadı."


def _disk() -> str:
    if HAS_PSUTIL:
        lines = []
        for part in psutil.disk_partitions():
            if "cdrom" in part.opts.lower() or not part.fstype:
                continue
            try:
                du = psutil.disk_usage(part.mountpoint)
                total = du.total / (1024**3)
                used  = du.used  / (1024**3)
                free  = du.free  / (1024**3)
                pct   = du.percent
                lines.append(
                    f"Disk {part.device}: {used:.1f} GB kullanıldı, "
                    f"{free:.1f} GB boş (toplam {total:.1f} GB, %{pct:.0f} dolu)"
                )
            except PermissionError:
                continue
        if lines:
            return "\n".join(lines)
    # PowerShell fallback
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-PSDrive -PSProvider FileSystem | "
             "Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,1)}}, "
             "@{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}} | Format-Table -AutoSize"],
            text=True, timeout=8, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            return f"Disk bilgisi:\n{out}"
    except Exception:
        pass
    return "Disk bilgisi alınamadı."


def _network() -> str:
    # psutil ile ağ istatistikleri
    if HAS_PSUTIL:
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            lines = []
            for iface, addr_list in addrs.items():
                if iface == "lo" or iface.startswith("Loopback"):
                    continue
                iface_stats = stats.get(iface)
                if iface_stats and not iface_stats.isup:
                    continue
                for addr in addr_list:
                    if addr.family.name == "AF_INET":
                        lines.append(f"  {iface}: {addr.address}")
            if lines:
                result = "Ağ bağlantıları:\n" + "\n".join(lines)
            else:
                result = "Aktif ağ bağlantısı bulunamadı."
        except Exception:
            result = ""
    else:
        result = ""

    # WiFi SSID — Windows
    try:
        wifi_out = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            text=True, timeout=5, stderr=subprocess.DEVNULL
        )
        for line in wifi_out.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[-1].strip()
                if ssid:
                    result = f"WiFi: {ssid} bağlı\n" + result
                    break
    except Exception:
        pass

    return result or "Ağ bilgisi alınamadı."


def _uptime() -> str:
    if HAS_PSUTIL:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        now  = datetime.datetime.now()
        delta = now - boot
        hours   = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"Sistem açık: {hours} saat {minutes} dakika (Açılış: {boot.strftime('%d.%m.%Y %H:%M')})"
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Date) - (gcim Win32_OperatingSystem).LastBootUpTime | "
             "Select-Object -ExpandProperty TotalHours"],
            text=True, timeout=5, stderr=subprocess.DEVNULL
        ).strip()
        if out:
            h = float(out)
            return f"Sistem açık: yaklaşık {h:.1f} saat"
    except Exception:
        pass
    return "Çalışma süresi alınamadı."


def _top_processes() -> str:
    if HAS_PSUTIL:
        procs = []
        for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
            try:
                procs.append((p.info["cpu_percent"] or 0, p.info["name"]))
            except Exception:
                continue
        procs.sort(reverse=True)
        top = procs[:8]
        lines = ["En yüksek CPU kullanan prosesler:"]
        for cpu, name in top:
            lines.append(f"  {name:<30} %{cpu:.1f} CPU")
        return "\n".join(lines)
    return "Proses listesi psutil olmadan alınamaz."
