"""
E-posta Yöneticisi — F.R.I.D.A.Y
SMTP ile e-posta gönderir (dosya eki destekli) ve IMAP ile gelen kutusu okur.
"""

import smtplib
import imaplib
import email
import os
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from pathlib import Path
from typing import List, Optional

from app_config import get_app_config_value

# ── Bilinen SMTP/IMAP ayarları ─────────────────────────────────────────────
PROVIDER_SETTINGS = {
    "gmail": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "note": "Gmail için 'Uygulama Şifresi' (App Password) kullanın.",
    },
    "outlook": {
        "smtp_host": "smtp-mail.outlook.com",
        "smtp_port": 587,
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "note": "Outlook / Hotmail / Live hesapları desteklenir.",
    },
    "hotmail": {
        "smtp_host": "smtp-mail.outlook.com",
        "smtp_port": 587,
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "note": "Hotmail = Outlook altyapısı.",
    },
    "yahoo": {
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "note": "Yahoo için uygulama şifresi gereklidir.",
    },
    "yandex": {
        "smtp_host": "smtp.yandex.com",
        "smtp_port": 587,
        "imap_host": "imap.yandex.com",
        "imap_port": 993,
        "note": "",
    },
}


def _detect_provider(email_addr: str) -> dict:
    domain = email_addr.lower().split("@")[-1] if "@" in email_addr else ""
    for key, settings in PROVIDER_SETTINGS.items():
        if key in domain:
            return settings
    # Özel SMTP — config'den al
    return {
        "smtp_host": str(get_app_config_value("email_smtp_host", "") or ""),
        "smtp_port": int(get_app_config_value("email_smtp_port", 587) or 587),
        "imap_host": str(get_app_config_value("email_imap_host", "") or ""),
        "imap_port": int(get_app_config_value("email_imap_port", 993) or 993),
        "note": "",
    }


def _get_credentials() -> tuple[str, str]:
    """Kayıtlı e-posta adresini ve şifreyi döndürür."""
    addr = str(get_app_config_value("email_address", "") or "").strip()
    pwd = str(get_app_config_value("email_password", "") or "").strip()
    return addr, pwd


def _resolve_attachment(path_str: str) -> Optional[Path]:
    """Ek dosyasının yolunu çözer."""
    common = {
        "masaüstü": Path.home() / "Desktop",
        "desktop": Path.home() / "Desktop",
        "indirilenler": Path.home() / "Downloads",
        "downloads": Path.home() / "Downloads",
    }
    key = path_str.strip().lower()
    if key in common:
        return None  # Klasör, dosya değil

    p = Path(path_str).expanduser()
    if not p.is_absolute():
        # Masaüstünde ara
        desktop = Path.home() / "Desktop" / path_str
        if desktop.exists():
            return desktop
        p = Path.home() / p
    return p if p.exists() else None


def send_email(
    to: str,
    subject: str,
    body: str,
    attachments: Optional[List[str]] = None,
    cc: Optional[str] = None,
    from_name: Optional[str] = None,
) -> str:
    """
    E-posta gönderir.
    to: alıcı adresi veya "Ad <adres>" formatı
    subject: konu
    body: mesaj metni
    attachments: dosya yolu listesi (opsiyonel)
    cc: CC adresi (opsiyonel)
    from_name: gönderici adı (opsiyonel, varsayılan config'den alınır)
    """
    sender, password = _get_credentials()

    if not sender:
        return (
            "❌ E-posta adresi ayarlanmamış!\n"
            "Lütfen şunu söyleyin: 'E-posta adresimi kaydet: ornek@gmail.com' "
            "ve 'E-posta şifremi kaydet: ****'"
        )
    if not password:
        return (
            "❌ E-posta şifresi ayarlanmamış!\n"
            "Gmail kullanıyorsanız Google hesabınızda 'Uygulama Şifresi' (App Password) oluşturun."
        )
    if not to:
        return "❌ Alıcı e-posta adresi belirtilmedi."
    if not subject:
        subject = "F.R.I.D.A.Y — Mesaj"
    if not body:
        return "❌ Mesaj içeriği boş olamaz."

    prov = _detect_provider(sender)
    smtp_host = prov["smtp_host"]
    smtp_port = prov["smtp_port"]

    if not smtp_host:
        return "❌ SMTP sunucusu bulunamadı. Lütfen config'de email_smtp_host ayarlayın."

    # Mesaj oluştur
    msg = MIMEMultipart()
    display_name = from_name or str(get_app_config_value("email_display_name", "F.R.I.D.A.Y") or "F.R.I.D.A.Y")
    msg["From"] = f"{display_name} <{sender}>"
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Ekleri ekle
    attachment_results = []
    if attachments:
        for att_str in attachments:
            att_path = _resolve_attachment(att_str)
            if att_path and att_path.is_file():
                try:
                    with open(att_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{att_path.name}"'
                    )
                    msg.attach(part)
                    attachment_results.append(f"  📎 {att_path.name}")
                except Exception as e:
                    attachment_results.append(f"  ⚠️ {att_str} eklenemedi: {e}")
            else:
                attachment_results.append(f"  ⚠️ Dosya bulunamadı: {att_str}")

    # Gönder
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)

            recipients = [to]
            if cc:
                recipients.extend(c.strip() for c in cc.split(","))

            server.sendmail(sender, recipients, msg.as_string())

        lines = [
            f"✅ E-posta gönderildi!",
            f"  📨 Kime: {to}",
            f"  📌 Konu: {subject}",
        ]
        if attachment_results:
            lines.append("  Ekler:")
            lines.extend(attachment_results)
        return "\n".join(lines)

    except smtplib.SMTPAuthenticationError:
        return (
            "❌ Kimlik doğrulama hatası!\n"
            "Gmail kullanıyorsanız normal şifre değil, 'Uygulama Şifresi' (App Password) girmeniz gerekiyor.\n"
            "Google Hesabı → Güvenlik → 2 Adımlı Doğrulama → Uygulama Şifreleri"
        )
    except smtplib.SMTPException as e:
        return f"❌ SMTP hatası: {e}"
    except ConnectionRefusedError:
        return f"❌ Bağlantı reddedildi ({smtp_host}:{smtp_port})"
    except TimeoutError:
        return f"❌ Bağlantı zaman aşımı ({smtp_host})"
    except Exception as e:
        return f"❌ E-posta gönderilemedi: {e}"


def read_emails(folder: str = "INBOX", count: int = 5, unread_only: bool = True) -> str:
    """
    IMAP ile gelen kutusunu okur.
    folder: INBOX | Sent | Junk vb.
    count: okunacak mesaj sayısı
    unread_only: sadece okunmamışlar
    """
    sender, password = _get_credentials()

    if not sender or not password:
        return "❌ E-posta bilgileri ayarlanmamış. 'E-posta adresimi kaydet' diyerek başlayın."

    prov = _detect_provider(sender)
    imap_host = prov["imap_host"]
    imap_port = prov["imap_port"]

    if not imap_host:
        return "❌ IMAP sunucusu bulunamadı."

    try:
        with imaplib.IMAP4_SSL(imap_host, imap_port) as mail:
            mail.login(sender, password)
            mail.select(folder)

            search_criteria = "UNSEEN" if unread_only else "ALL"
            _, msg_ids = mail.search(None, search_criteria)

            if not msg_ids or not msg_ids[0]:
                label = "okunmamış" if unread_only else "toplam"
                return f"📭 {folder} klasöründe {label} e-posta yok."

            id_list = msg_ids[0].split()
            # Son N mesaj
            selected = id_list[-count:][::-1]

            results = []
            for msg_id in selected:
                try:
                    _, msg_data = mail.fetch(msg_id, "(RFC822)")
                    if not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    if not isinstance(raw, bytes):
                        continue
                    msg_obj = email.message_from_bytes(raw)

                    # Konu
                    subj_raw = msg_obj.get("Subject", "(Konu yok)")
                    subj_parts = decode_header(subj_raw)
                    subject = ""
                    for part, enc in subj_parts:
                        if isinstance(part, bytes):
                            subject += part.decode(enc or "utf-8", errors="replace")
                        else:
                            subject += str(part)

                    # Gönderici
                    from_raw = msg_obj.get("From", "Bilinmiyor")
                    from_parts = decode_header(from_raw)
                    from_str = ""
                    for part, enc in from_parts:
                        if isinstance(part, bytes):
                            from_str += part.decode(enc or "utf-8", errors="replace")
                        else:
                            from_str += str(part)

                    # Tarih
                    date_str = msg_obj.get("Date", "")
                    try:
                        dt = email.utils.parsedate_to_datetime(date_str)
                        date_fmt = dt.strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        date_fmt = date_str[:25] if date_str else "—"

                    # Gövde
                    body = ""
                    if msg_obj.is_multipart():
                        for part in msg_obj.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    charset = part.get_content_charset() or "utf-8"
                                    body = part.get_payload(decode=True).decode(charset, errors="replace")
                                    break
                                except Exception:
                                    pass
                    else:
                        try:
                            charset = msg_obj.get_content_charset() or "utf-8"
                            body = msg_obj.get_payload(decode=True).decode(charset, errors="replace")
                        except Exception:
                            body = "(İçerik okunamadı)"

                    # İlk 300 karakter
                    body_preview = body.strip()[:300].replace("\n", " ")
                    if len(body.strip()) > 300:
                        body_preview += "..."

                    results.append(
                        f"📧 Kimden: {from_str}\n"
                        f"   Konu: {subject}\n"
                        f"   Tarih: {date_fmt}\n"
                        f"   İçerik: {body_preview}"
                    )

                except Exception as e:
                    results.append(f"⚠️ Mesaj okunamadı: {e}")

            if not results:
                return f"📭 {folder} klasöründe okunacak mesaj yok."

            header = f"📬 {folder} — Son {len(results)} Mesaj\n{'═'*55}"
            return header + "\n\n" + f"\n{'─'*55}\n".join(results)

    except imaplib.IMAP4.error as e:
        return f"❌ IMAP hatası: {e}"
    except Exception as e:
        return f"❌ E-posta okuma hatası: {e}"


def save_email_credentials(address: str, password: str, display_name: str = "") -> str:
    """E-posta kimlik bilgilerini config'e kaydeder."""
    from app_config import save_app_config
    updates: dict = {
        "email_address": address.strip(),
        "email_password": password.strip(),
    }
    if display_name:
        updates["email_display_name"] = display_name.strip()
    save_app_config(updates)

    prov = _detect_provider(address)
    lines = [f"✅ E-posta bilgileri kaydedildi: {address}"]
    if prov.get("note"):
        lines.append(f"ℹ️  {prov['note']}")
    return "\n".join(lines)
