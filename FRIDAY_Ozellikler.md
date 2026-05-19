# 🤖 F.R.I.D.A.Y. — Yapay Zeka Asistanı Yetenek Rehberi

> **F**emale **R**eplacement **I**ntelligent **D**igital **A**ssistant **Y**outh  
> Geliştirici: Samet Oymak | Versiyon: 2026 Pro

---

## 1. 🖥️ Sistem & Donanım Kontrolü

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| Ses Kontrolü | `set_volume` | Sesi ayarla, artır veya kıs |
| Parlaklık | `set_brightness` | Ekran parlaklığını değiştir |
| Sistem Bilgisi | `sys_info` | CPU, RAM, disk, pil, ağ, saat/tarih |
| PowerShell | `shell_run` | Windows komutlarını çalıştır |
| Sistem Kapatma | `sys_control` | Kapat / Yeniden başlat / Uyku |
| Akıllı Ev (Arduino) | `send_arduino_command` | Işık, röle, sensör kontrolü |
| Tablet Kontrolü | `tablet_control` | Bağlı tablet komutları |

---

## 2. 💬 İletişim & Organizasyon

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| WhatsApp Mesaj | `send_whatsapp_message` | Mesaj gönder veya taslak oluştur |
| WhatsApp Kişi | `save_whatsapp_contact` | Rehbere yeni kişi ekle |
| E-posta Gönder | `send_email` | SMTP üzerinden e-posta gönder |
| E-posta Oku | `read_emails` | Gelen kutusunu listele ve oku |
| Takvim Yönetimi | `get/add/delete_calendar_event` | Google Takvim entegrasyonu |
| Anımsatıcılar | `get/add_reminder` | Anımsatıcı oluştur ve listele |
| Bildirimler | `read_notifications` | Windows bildirimlerini oku ve özetle |
| Namaz Vakitleri | `namaz_vakti_arayan` | İstanbul namaz vakitlerini getir |

---

## 3. 📂 Dosya & Kod Yönetimi

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| Dosya Yöneticisi | `file_manager` | Listele, ara, kopyala, taşı, sil, arşivle |
| Dosya Oku/Yaz | `read_file` / `write_file` | Metin dosyası işlemleri |
| Kod Düzenleme | `replace_code` | Belirli kod bloğunu değiştir |
| Kod Çalıştırma | `execute_code` | Python kodu doğrudan çalıştır |
| Test Koştur | `run_tests` | Birim testlerini otomatik çalıştır |
| GitHub Yönetimi | `github_manager` | Push, branch oluştur, PR aç |
| Büyük Dosya Bul | `file_manager` | Disk temizliği için büyük/yinelenen dosyalar |

---

## 4. 🌐 Multimedya & Web

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| Tarayıcı Kontrolü | `browser_control` | URL aç, Google'da ara |
| YouTube Oynat | `browser_control` | YouTube'da video veya müzik çal |
| Spotify / Apple Music | `play_media` | Platform üzerinde içerik oynat |
| YouTube Analiz | `get_youtube_channel_report` | Kanal istatistikleri ve rapor |
| Hisse Danışmanı | `stock_advisor` | Borsa analizi ve hisse takibi |
| DuckDuckGo Arama | `search_duckduckgo` | Otonom web araması (ajan içi) |
| Wallpaper | `wallpaper_manager` | Masaüstü duvar kağıdını değiştir |

---

## 5. 🎮 Oyun Asistanı (Game Helper Pro)

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| Steam Oyun Başlat | `launch_steam_game` | İsimden arayarak Steam oyunu başlat |
| Auto-Clicker Makro | `auto_clicker` | Saniyede X tıklama makrosu |
| Tuş Basılı Tut | `hold_key` | Klavye tuşunu süre boyunca tut |
| Tuş Dizisi | `press_keys_sequence` | Kombo/skill dizisi çalıştır |
| Fare Basılı Tut | `hold_click` | Sol/sağ tık basılı tut |
| Nişangah Overlay | `toggle_crosshair` | Dot / Cross / Circle / T-Shape nişangah |
| Game Booster | `boost_game_performance` | Oyuna High CPU önceliği ver |
| **PRO Triggerbot** | `triggerbot_color_change` | numpy HSV renk tespiti ile otonom atış |
| Anti-AFK Bot | `anti_afk_bot` | Sunucudan atılmayı önle |

### 🎯 Triggerbot Oyun Önayarları
`cs2` · `valorant` · `apex` · `pubg` · `fortnite` · `red` · `yellow` · `white` · `any`

---

## 6. 🧠 Yapay Zeka & Görü (Vision)

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| Kamera Analizi | `analyze_camera` | Gemini AI ile kameradan nesne tanı |
| Boyut/Hacim Tahmini | `analyze_camera` | Görüntüden boyut, alan, hacim hesapla |
| Plaka Okuma (OCR) | `analyze_camera` | Araç plakasını kameradan oku |
| Eğim Analizi | `analyze_camera` | Cismin düz/eğik olup olmadığını söyle |
| Ekran Analizi | `analyze_screen` | Aktif pencereyi AI ile analiz et |
| Ekran Tıklama | `click_on_screen` | AI ile belirli öğeye tıkla |
| Yüz Kaydetme | `register_face` | Profil yüzünü sisteme kaydet |

---

## 7. 🛡️ Güvenlik & Nöbetçi Protokolü

| Özellik | Komut / Fonksiyon | Açıklama |
|---|---|---|
| **Nöbetçi Modu** | `start_sentinel_mode` | Kamera ile hareket algıla |
| Yüz Tanıma | Sentinel + Gemini AI | Samet mi, yabancı mı? otomatik karar |
| Davetsiz Misafir Fotoğrafı | `security_captures/` | Hareket anında fotoğraf kaydet |
| WhatsApp Alarm | Sentinel + WhatsApp | Yabancı tespitinde fotoğraflı uyarı gönder |
| **Jest Kontrolü** | `start_gesture_control` | El hareketleriyle medya kontrolü |

### 🤚 Desteklenen Jestler
| Jest | Eylem |
|---|---|
| Sağa kaydır | ⏭ Sonraki şarkı |
| Sola kaydır | ⏮ Önceki şarkı |
| Yukarı kaydır | 🔊 Sesi artır (+10) |
| Aşağı kaydır | 🔉 Sesi azalt (-10) |
| Hareketsiz kal | ⏯ Duraklat / Devam |

---

## 8. ⚕️ Sağlık Takibi (iPhone Entegrasyonu)

> iPhone'dan iCloud üzerinden **Health Auto Export** ile senkronize edilir.

| Metrik | Açıklama |
|---|---|
| 💓 Nabız / Dinlenim Nabzı / HRV | Anlık ve ortalama kalp verileri |
| 🩸 Kan Oksijeni (SpO2) | Yüzde değeriyle anlık ölçüm |
| 👣 Adım Sayısı & Mesafe | Günlük yürüyüş verisi |
| 🔥 Aktif & Bazal Kalori | Yakılan enerji miktarı |
| 🏃 Egzersiz Süresi & Analizi | Antrenman penceresi ve yük yorumu |
| 💤 Uyku Analizi | Uyku süresi, derin uyku, REM |
| 🚀 Yürüme Hızı & Adım Uzunluğu | Mobilite metrikleri |
| 🎧 Ses Maruziyeti | Çevresel & kulaklık dB değerleri |
| 🌤 Gün Işığı Süresi | Günlük güneş maruziyeti |

---

## 9. 🤖 Otonom Kod Geliştirici

> Sadece bir görev tanımla — F.R.I.D.A.Y. kodlar, test eder, GitHub'a gönderir!

### Çalışma Akışı
```
1. 🔍 İnternet Araması  →  DuckDuckGo ile güncel döküman çek
2. 💻 Geliştirici Ajan  →  Gemini 2.5 Flash veya Ollama ile kod üret
3. 🔒 Güvenlik Taraması →  Bandit + Pylint statik analiz
4. ▶️  Sandbox Çalıştır  →  İzole Python venv içinde test et
5. 📦 Oto Paket Kurulum →  Eksik kütüphaneleri otomatik kur
6. 🧪 Testçi Ajan       →  pytest ile otomatik test yaz ve koştur
7. 🚀 GitHub PR          →  Branch aç, commit et, Pull Request oluştur
```

### Desteklenen Backend'ler
- **Gemini 2.5 Flash** (varsayılan, bulut)
- **Yerel Ollama** — `qwen`, `deepseek`, `llama`, `gemma` modelleri
- **Oto Fallback** — API limiti aşılırsa Ollama'ya geç

---

## 10. 📋 Görev & Protokoller

| Protokol | Komut | Açıklama |
|---|---|---|
| Sabah Protokolü | `sabah_protokolu` | Hava durumu, sağlık özeti, sistem sağlığı |
| Ben Çıkıyorum | `ben_cikiyorum` | Ekranı kapat, güvenli bekle |
| Ben Geldim | `ben_geldim` | Karşılama mesajı ve günlük brifing |
| Görev Planlama | `create_task_plan` | Karmaşık görevleri adımlara böl |
| Görev Yürütme | `execute_task_plan` | Planı otonom olarak uygula |
| Görev İptal | `cancel_task` | Çalışan görevi durdur |

---

## 11. 🧠 Bellek & Kişiselleştirme

| Özellik | Açıklama |
|---|---|
| `save_memory` | Kullanıcı tercihlerini ve önemli bilgileri kalıcı kaydet |
| `delete_memory` | Kaydedilmiş bir bilgiyi sil |
| Ses Kimlik Doğrulama | `voice_auth` — Sesle giriş |
| Klap Başlatıcı | `clap_launcher` — El çırpmayla uygulama aç |
| Alarm & Zamanlayıcı | `set_alarm` / `set_timer` — Ses bildirimli |
| Hava Durumu | `get_weather` — Anlık hava bilgisi |

---

## 12. ⚡ Teknik Altyapı

```
• Dil           : Python 3.12+
• Ana AI Motor  : Google Gemini 2.5 Flash
• Yerel AI      : Ollama (qwen/deepseek/llama)
• Görü Motoru   : OpenCV + numpy HSV (10-50x hız avantajı)
• UI Framework  : PyQt / Tkinter Overlay + Web HUD
• Otomasyon     : PyAutoGUI
• Güvenlik Tarama: Bandit + Pylint
• Test Koşucu   : pytest
• VCS           : Git + GitHub API (PR otomasyonu)
• Arduino       : Serial COM iletişimi (akıllı ev)
• Mobil Köprü   : Telegram Bot (uzaktan kontrol)
```

---

*Son güncelleme: Mayıs 2026 — F.R.I.D.A.Y. Pro Edition*
