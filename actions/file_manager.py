"""
Gelişmiş Dosya Yönetimi — Windows
Dosya listeleme, arama, kopyalama, taşıma, silme, arşivleme
"""

import os
import shutil
import hashlib
import zipfile
import datetime
from pathlib import Path
from typing import List

# Güvenlik: Bu yollara dokunulamaz
BLOCKED_PATHS = [
    "C:\\Windows\\System32",
    "C:\\Windows\\SysWOW64",
    "C:\\Program Files\\Windows",
    "C:\\Windows\\Boot",
]

COMMON_SHORTCUTS = {
    "masaüstü": Path.home() / "Desktop",
    "desktop": Path.home() / "Desktop",
    "indirilenler": Path.home() / "Downloads",
    "downloads": Path.home() / "Downloads",
    "belgeler": Path.home() / "Documents",
    "documents": Path.home() / "Documents",
    "resimler": Path.home() / "Pictures",
    "pictures": Path.home() / "Pictures",
    "müzik": Path.home() / "Music",
    "music": Path.home() / "Music",
    "videolar": Path.home() / "Videos",
    "videos": Path.home() / "Videos",
    "ev": Path.home(),
    "home": Path.home(),
}


def _resolve_path(path_str: str) -> Path:
    """Yol kısayollarını ve ~ genişletmelerini çözer."""
    if not path_str:
        return Path.home() / "Desktop"
    key = path_str.strip().lower()
    if key in COMMON_SHORTCUTS:
        return COMMON_SHORTCUTS[key]
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = Path.home() / p
    return p


def _is_blocked(path: Path) -> bool:
    path_str = str(path).upper()
    for blocked in BLOCKED_PATHS:
        if path_str.startswith(blocked.upper()):
            return True
    return False


def _human_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def list_directory(path: str = "masaüstü", show_hidden: bool = False, sort_by: str = "name") -> str:
    """Klasör içeriğini boyut, tarih ve tür bilgisiyle listeler."""
    p = _resolve_path(path)
    if not p.exists():
        return f"Klasör bulunamadı: {p}"
    if not p.is_dir():
        return f"Bu bir klasör değil: {p}"

    try:
        items = []
        for entry in p.iterdir():
            if not show_hidden and entry.name.startswith("."):
                continue
            try:
                stat = entry.stat()
                size = stat.st_size if entry.is_file() else 0
                modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M")
                item_type = "📁" if entry.is_dir() else "📄"
                items.append((entry.name, item_type, size, modified, entry.is_dir()))
            except PermissionError:
                items.append((entry.name, "🔒", 0, "—", entry.is_dir()))

        # Sıralama
        if sort_by == "size":
            items.sort(key=lambda x: x[2], reverse=True)
        elif sort_by == "date":
            items.sort(key=lambda x: x[3], reverse=True)
        else:
            items.sort(key=lambda x: (not x[4], x[0].lower()))

        if not items:
            return f"Klasör boş: {p}"

        lines = [f"📂 {p}\n{'─'*50}"]
        for name, icon, size, modified, is_dir in items:
            size_str = "—" if is_dir else _human_size(size)
            lines.append(f"{icon} {name:<35} {size_str:>10}  {modified}")

        lines.append(f"\n{'─'*50}")
        lines.append(f"Toplam: {len(items)} öğe")
        return "\n".join(lines)

    except PermissionError:
        return f"Bu klasöre erişim izni yok: {p}"
    except Exception as e:
        return f"Hata: {e}"


def search_files(path: str = "masaüstü", pattern: str = "*", content_search: str = "") -> str:
    """Dosya adı veya içeriğe göre arama yapar."""
    p = _resolve_path(path)
    if not p.exists():
        return f"Klasör bulunamadı: {p}"

    try:
        found = []
        search_pattern = f"*{pattern}*" if "*" not in pattern else pattern

        for entry in p.rglob(search_pattern):
            try:
                if content_search and entry.is_file():
                    try:
                        text = entry.read_text(encoding="utf-8", errors="ignore")
                        if content_search.lower() not in text.lower():
                            continue
                    except Exception:
                        continue
                stat = entry.stat()
                rel = entry.relative_to(p)
                size_str = _human_size(stat.st_size) if entry.is_file() else "klasör"
                found.append(f"{'📁' if entry.is_dir() else '📄'} {rel}  ({size_str})")
            except Exception:
                continue

        if not found:
            msg = f"'{pattern}'"
            if content_search:
                msg += f" (içerik: '{content_search}')"
            return f"Arama sonucu bulunamadı: {msg} — {p}"

        lines = [f"🔍 Arama: '{pattern}' içinde {p}\n{'─'*50}"]
        lines.extend(found[:100])
        if len(found) > 100:
            lines.append(f"... ve {len(found)-100} sonuç daha.")
        lines.append(f"\n{'─'*50}\nToplam {len(found)} sonuç.")
        return "\n".join(lines)

    except Exception as e:
        return f"Arama hatası: {e}"


def copy_item(src: str, dst: str) -> str:
    """Dosya veya klasörü kopyalar."""
    src_path = _resolve_path(src)
    dst_path = _resolve_path(dst)

    if _is_blocked(src_path) or _is_blocked(dst_path):
        return "Güvenlik: Bu işlem engellendi (sistem klasörü korunuyor)."
    if not src_path.exists():
        return f"Kaynak bulunamadı: {src_path}"

    try:
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path / src_path.name, dirs_exist_ok=True)
        else:
            dst_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path / src_path.name)
        return f"✅ Kopyalandı: {src_path.name} → {dst_path}"
    except Exception as e:
        return f"Kopyalama hatası: {e}"


def move_item(src: str, dst: str) -> str:
    """Dosya veya klasörü taşır / yeniden adlandırır."""
    src_path = _resolve_path(src)
    dst_path = _resolve_path(dst)

    if _is_blocked(src_path) or _is_blocked(dst_path):
        return "Güvenlik: Bu işlem engellendi."
    if not src_path.exists():
        return f"Kaynak bulunamadı: {src_path}"

    try:
        # Hedef bir klasörse içine taşı
        if dst_path.is_dir():
            dst_path = dst_path / src_path.name
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        return f"✅ Taşındı: {src_path.name} → {dst_path}"
    except Exception as e:
        return f"Taşıma hatası: {e}"


def delete_item(path: str, permanent: bool = False) -> str:
    """Dosya veya klasörü çöp kutusuna taşır ya da kalıcı siler."""
    p = _resolve_path(path)

    if _is_blocked(p):
        return "Güvenlik: Bu klasör silinemez."
    if not p.exists():
        return f"Bulunamadı: {p}"

    try:
        if permanent:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            return f"🗑️ Kalıcı olarak silindi: {p.name}"
        else:
            # Windows Recycle Bin'e gönder
            try:
                from send2trash import send2trash  # type: ignore
                send2trash(str(p))
                return f"🗑️ Çöp kutusuna taşındı: {p.name}"
            except ImportError:
                # Fallback: kalıcı sil ama uyar
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                return f"⚠️ 'send2trash' yüklü değil — kalıcı silindi: {p.name}"
    except PermissionError:
        return f"Silme izni yok: {p.name}"
    except Exception as e:
        return f"Silme hatası: {e}"


def create_folder(path: str) -> str:
    """Yeni bir klasör oluşturur."""
    p = _resolve_path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        return f"✅ Klasör oluşturuldu: {p}"
    except Exception as e:
        return f"Klasör oluşturma hatası: {e}"


def get_file_info(path: str) -> str:
    """Dosya hakkında ayrıntılı bilgi verir."""
    p = _resolve_path(path)
    if not p.exists():
        return f"Bulunamadı: {p}"

    try:
        stat = p.stat()
        created = datetime.datetime.fromtimestamp(stat.st_ctime).strftime("%d.%m.%Y %H:%M:%S")
        modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M:%S")
        size_str = _human_size(stat.st_size)
        kind = "Klasör" if p.is_dir() else "Dosya"
        ext = p.suffix.upper() if p.suffix else "—"

        lines = [
            f"📄 {p.name}",
            f"  Tür     : {kind} ({ext})",
            f"  Boyut   : {size_str}",
            f"  Konum   : {p.parent}",
            f"  Oluşturma: {created}",
            f"  Değiştirme: {modified}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Bilgi alınamadı: {e}"


def compress_files(paths: List[str], output: str = "") -> str:
    """Dosya veya klasörleri ZIP arşivi olarak sıkıştırır."""
    if not paths:
        return "Sıkıştırılacak dosya belirtilmedi."

    first_path = _resolve_path(paths[0])
    if not output:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = first_path.parent / f"arşiv_{ts}.zip"
    else:
        output_path = _resolve_path(output)
        if output_path.suffix.lower() != ".zip":
            output_path = output_path.with_suffix(".zip")

    try:
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path_str in paths:
                p = _resolve_path(path_str)
                if p.is_dir():
                    for file in p.rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(p.parent))
                elif p.is_file():
                    zf.write(p, p.name)
                else:
                    continue

        size_str = _human_size(output_path.stat().st_size)
        return f"✅ Arşiv oluşturuldu: {output_path.name} ({size_str})\nKonum: {output_path.parent}"
    except Exception as e:
        return f"Arşivleme hatası: {e}"


def extract_archive(archive: str, dest: str = "") -> str:
    """ZIP arşivini çıkarır."""
    p = _resolve_path(archive)
    if not p.exists():
        return f"Arşiv bulunamadı: {p}"

    dest_path = _resolve_path(dest) if dest else p.parent / p.stem

    try:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p, "r") as zf:
                zf.extractall(dest_path)
        else:
            shutil.unpack_archive(str(p), str(dest_path))

        return f"✅ Çıkarıldı: {p.name} → {dest_path}"
    except Exception as e:
        return f"Çıkarma hatası: {e}"


def find_large_files(path: str = "masaüstü", min_mb: float = 50.0) -> str:
    """Belirli boyutun üzerindeki dosyaları bulur."""
    p = _resolve_path(path)
    if not p.exists():
        return f"Klasör bulunamadı: {p}"

    min_bytes = min_mb * 1024 * 1024
    found = []

    try:
        for entry in p.rglob("*"):
            if entry.is_file():
                try:
                    size = entry.stat().st_size
                    if size >= min_bytes:
                        rel = entry.relative_to(p)
                        found.append((size, str(rel)))
                except Exception:
                    continue

        found.sort(reverse=True)

        if not found:
            return f"{min_mb:.0f} MB'tan büyük dosya bulunamadı: {p}"

        lines = [f"🔍 {min_mb:.0f} MB+ dosyalar — {p}\n{'─'*50}"]
        for size, name in found[:50]:
            lines.append(f"📄 {name:<50} {_human_size(size):>10}")
        if len(found) > 50:
            lines.append(f"... ve {len(found)-50} dosya daha.")
        lines.append(f"\n{'─'*50}\nToplam {len(found)} büyük dosya.")
        return "\n".join(lines)

    except Exception as e:
        return f"Arama hatası: {e}"


def find_duplicates(path: str = "masaüstü") -> str:
    """Hash karşılaştırmasıyla aynı içerikli dosyaları bulur."""
    p = _resolve_path(path)
    if not p.exists():
        return f"Klasör bulunamadı: {p}"

    hashes: dict = {}
    try:
        for entry in p.rglob("*"):
            if entry.is_file():
                try:
                    h = hashlib.md5(entry.read_bytes()).hexdigest()
                    hashes.setdefault(h, []).append(entry)
                except Exception:
                    continue

        dupes = {h: files for h, files in hashes.items() if len(files) > 1}

        if not dupes:
            return f"Yinelenen dosya bulunamadı: {p}"

        lines = [f"🔁 Yinelenen Dosyalar — {p}\n{'─'*50}"]
        total = 0
        for h, files in list(dupes.items())[:20]:
            size = files[0].stat().st_size
            lines.append(f"\nGrup ({_human_size(size)} × {len(files)}):")
            for f in files:
                lines.append(f"  📄 {f.relative_to(p)}")
            total += len(files) - 1

        lines.append(f"\n{'─'*50}\n{total} yinelenen dosya bulundu.")
        return "\n".join(lines)

    except Exception as e:
        return f"Yinelenen dosya arama hatası: {e}"


def get_folder_size(path: str) -> str:
    """Bir klasörün toplam boyutunu hesaplar."""
    p = _resolve_path(path)
    if not p.exists():
        return f"Bulunamadı: {p}"

    total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    file_count = sum(1 for f in p.rglob("*") if f.is_file())
    return f"📂 {p.name}: {_human_size(total)} ({file_count} dosya)"


def file_manager(action: str, **kwargs) -> str:
    """
    Merkezi dosya yönetim arayüzü.
    action: list | search | copy | move | delete | create_folder |
            info | compress | extract | find_large | find_duplicates | folder_size
    """
    action = action.strip().lower()

    dispatch = {
        "list":            lambda: list_directory(
                               kwargs.get("path", "masaüstü"),
                               bool(kwargs.get("show_hidden", False)),
                               kwargs.get("sort_by", "name")),
        "search":          lambda: search_files(
                               kwargs.get("path", "masaüstü"),
                               kwargs.get("pattern", "*"),
                               kwargs.get("content_search", "")),
        "copy":            lambda: copy_item(kwargs.get("src", ""), kwargs.get("dst", "")),
        "move":            lambda: move_item(kwargs.get("src", ""), kwargs.get("dst", "")),
        "delete":          lambda: delete_item(
                               kwargs.get("path", ""),
                               bool(kwargs.get("permanent", False))),
        "create_folder":   lambda: create_folder(kwargs.get("path", "")),
        "info":            lambda: get_file_info(kwargs.get("path", "")),
        "compress":        lambda: compress_files(
                               kwargs.get("paths", []),
                               kwargs.get("output", "")),
        "extract":         lambda: extract_archive(
                               kwargs.get("archive", ""),
                               kwargs.get("dest", "")),
        "find_large":      lambda: find_large_files(
                               kwargs.get("path", "masaüstü"),
                               float(kwargs.get("min_mb", 50))),
        "find_duplicates": lambda: find_duplicates(kwargs.get("path", "masaüstü")),
        "folder_size":     lambda: get_folder_size(kwargs.get("path", "")),
    }

    fn = dispatch.get(action)
    if fn is None:
        return (f"Bilinmeyen dosya yönetim işlemi: '{action}'. "
                f"Desteklenenler: {', '.join(dispatch.keys())}")
    return fn()
