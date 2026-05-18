# F.R.I.D.A.Y. Görev ve Özellikleri

## 1. Sistem ve Zaman Yönetimi 💻🕒
- **Ses Kontrolü:** `set_volume` (Sesi ayarlar, artırır, kısar) 🔊
- **Parlaklık Kontrolü:** `set_brightness` (Ekran parlaklığını ayarlar) 💡
- **Zamanlayıcı:** `set_timer` (Geri sayım sayacı kurar) ⏳
- **Alarm:** `set_alarm` (Belirli bir saat için alarm kurar) ⏰
- **Sistem Bilgisi:** `sys_info` (Pil, CPU, RAM, disk, saat, tarih, ağ durumu) 📊

## 2. İletişim ve Organizasyon 💬📅
- **WhatsApp Mesaj:** `send_whatsapp_message` (Mesaj gönderir veya taslak oluşturur) 📱
- **WhatsApp Kişi Kaydet:** `save_whatsapp_contact` (Rehbere kişi ekler) 👤
- **E-posta Gönder:** `send_email` (SMTP üzerinden e-posta gönderir) 📧
- **E-posta Oku:** `read_emails` (Gelen kutusunu okur) 📨
- **Takvim Yönetimi:** `get_calendar_events`, `add_calendar_event`, `delete_calendar_event` (Takvim etkinliklerini yönetir) 🗓️
- **Anımsatıcılar:** `get_reminders`, `add_reminder` (Anımsatıcı listelerini yönetir) ✅
- **Bildirimler:** `read_notifications`, `get_notification_summary` (Windows bildirimlerini okur ve özetler) 🔔

## 3. Dosya ve Kod Yönetimi 🗃️🐍
- **Dosya Yönetimi:** `file_manager` (Listeleme, arama, kopyalama, taşıma, silme, arşivleme, büyük/yinelenen dosya bulma) 📂
- **Dosya Okuma/Yazma:** `read_file`, `write_file` 📝
- **Kod Düzenleme:** `replace_code` (Kod bloklarını değiştirir) ✏️
- **Kod Çalıştırma:** `execute_code`, `run_tests` (Python kodu çalıştırır ve test eder) ▶️
- **Powershell:** `shell_run` (Windows PowerShell komutlarını çalıştırır) 💻

## 4. Multimedya ve Web 🌐🎧
- **Tarayıcı Kontrolü:** `browser_control` (URL açar, Google'da arar, YouTube'da oynatır) 🔎
- **Medya Oynatma:** `play_media` (Spotify, Apple Music, YouTube üzerinde içerik çalar) 🎶
- **YouTube Analiz:** `get_youtube_channel_report` (Kanal istatistiklerini raporlar) 📈

## 5. Yapay Zeka ve Otomasyon 🤖✨
- **Ekran Analizi:** `analyze_screen` (Aktif pencereyi analiz eder, metin okur, hata ayıklar) 🖥️
- **Kamera Analizi:** `analyze_camera` (Kameradan görüntü alır, nesne tanır, hacim/düzlük ölçer, plaka kaydeder) 📸
- **Ekran Etkileşimi:** `click_on_screen` (Ekranda belirli öğelere tıklar) 👆
- **Akıllı Ev (Arduino):** `send_arduino_command` (Işık, sıcaklık vb. kontrolü) 🏠
- **Kalıcı Hafıza:** `save_memory`, `delete_memory` (Kullanıcı tercihlerini ve önemli bilgileri kaydeder) 🧠

## 6. Protokoller 🛡️🔄
- **Sabah Protokolü:** `sabah_protokolu` (Günlük brifing, sistem sağlığı ve hava durumu) ☀️
- **Nöbetçi Modu:** `toggle_sentinel_mode` (Güvenlik modunu açar/kapatır) 🚨
- **Jest Kontrolü:** `toggle_gesture_control` (El hareketleriyle medya kontrolü) ✋
- **Yüz Kaydetme:** `yuz_kaydet` (Kullanıcı yüzünü kaydeder) 🙂
- **Ben Çıkıyorum:** `ben_cikiyorum` (Otomatik çıkış protokolü) 🚶
- **Ben Geldim:** `ben_geldim` (Otomatik dönüş protokolü) 🏠
- **Görev Planlama:** `create_task_plan`, `execute_task_plan`, `cancel_task` (Karmaşık görevleri planlar ve yürütür) 📋
