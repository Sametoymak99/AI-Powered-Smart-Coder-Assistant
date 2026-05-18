#!/usr/bin/env python3
"""
F.R.I.D.A.Y — Gercek zamanli sesli yardimci cekirdegi
Alp Ünlü tarafından yapılmıştır — @alppunlu
Windows ortamina uyarlanmis calisma akisi
"""

import asyncio
import datetime
import threading
import traceback
import os
import sys
import re
from pathlib import Path

if sys.stdout and getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import sounddevice as sd
from google import genai  # type: ignore[reportMissingImports]
from google.genai import types  # type: ignore[reportMissingImports]

from app_config import get_app_config_value
from ui import JarvisUI
from memory.memory_manager import load_memory, update_memory, delete_memory, format_memory_for_prompt
from actions.open_app import open_app, list_running_apps, kill_app
from actions.sys_info  import sys_info
from actions.calendar import get_calendar_events, add_calendar_event, delete_calendar_event
from actions.reminders import get_reminders, add_reminder
from actions.browser   import browser_control
from actions.shell     import shell_run
from actions.whatsapp  import send_whatsapp_message, save_whatsapp_contact
from actions.coder     import read_file, write_file, replace_code, execute_code, run_tests
from actions.media     import play_media
from actions.weather   import get_weather_summary
from actions.screen_vision import analyze_screen
from actions.youtube_stats import get_youtube_channel_report
from actions.notifications import read_notifications, read_whatsapp_messages, get_notification_summary
from actions.camera_vision import analyze_camera, start_sentinel_mode, stop_sentinel_mode, start_gesture_control, stop_gesture_control, is_sentinel_active, is_gesture_active, register_face
from actions.gui_control import click_on_screen
from actions.arduino_control import send_arduino_command, init_arduino, set_arduino_event_callback
from actions.file_manager import file_manager
from actions.email_manager import send_email, read_emails, save_email_credentials
from actions.task_planner import (
    create_plan, get_active_plan, cancel_plan, execute_plan, set_progress_callback
)
from actions.github_manager import push_to_github
from actions.sys_control import set_volume, set_brightness
from actions.alarms_timers import set_timer, set_alarm

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"


CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# ── Model ───────────────────────────────────────────────────────────────────
LIVE_MODEL = "models/gemini-2.5-flash-native-audio-latest"

# ── Audio ───────────────────────────────────────────────────────────────────
FORMAT           = 2  # pcm16 format (equivalent to pyaudio.paInt16)
CHANNELS         = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHUNK_SIZE       = 512   # Küçük chunk = daha az gecikme (~32ms @ 16kHz)
# Audio device - sounddevice doesn't require explicit initialization like PyAudio

# ── Tool tanımları ──────────────────────────────────────────────────────────
TOOL_DECLARATIONS = [
    {
        "name": "volume_up",
        "description": "Bilgisayarın sesini %10 artırır. Kullanıcı 'sesi artır', 'sesi yükselt' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "volume_down",
        "description": "Bilgisayarın sesini %10 azaltır. Kullanıcı 'sesi kıs', 'sesi azalt' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "set_volume",
        "description": "Bilgisayarın ses seviyesini belirli bir yüzdeye ayarlar. Kullanıcı 'sesi %50 yap', 'ses seviyesini 70'e getir' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level": {
                    "type": "NUMBER",
                    "description": "0 ile 100 arasında ses seviyesi yüzdesi."
                }
            },
            "required": ["level"]
        }
    },
    {
        "name": "get_health_data",
        "description": "Kullanıcının sağlık verilerini (adım, nabız, uyku vb.) analiz eder. Kullanıcı 'sağlık durumum nasıl', 'kaç adım attım' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Sorgu metni (örn: 'adım', 'uyku', 'nabız' veya 'all')"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "open_tablet_app",
        "description": "Android tablette bir uygulama açar. Kullanıcı 'tablette Spotify aç', 'tablette YouTube aç' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adı veya paket adı (örn: 'youtube', 'spotify', 'chrome' veya paket adı)"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "close_tablet_app",
        "description": "Android tablette bir uygulamayı kapatır. Kullanıcı 'tablette Spotify'ı kapat' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adı veya paket adı"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "open_app",
        "description": "Windows veya macOS'ta herhangi bir uygulama/program açar. Chrome, Spotify, Discord, VS Code, Hesap Makinesi, Dosya Gezgini, Görev Yöneticisi vb.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adı (örn. 'Spotify', 'Chrome', 'Discord', 'Hesap Makinesi')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "list_apps",
        "description": "Bilgisayarda şu an çalışan uygulamaları listeler. Kullanıcı 'hangi uygulamalar açık', 'çalışan programlar neler' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "kill_app",
        "description": "Bir uygulamayı/programı kapatır/sonlandırır. Kullanıcı 'kapat', 'sonlandır', 'uygulamayı öldür' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Kapatılacak uygulama adı. Örn: 'Chrome', 'Spotify', 'Discord'"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "sys_info",
        "description": "Sistem bilgisi alır: pil durumu, CPU, RAM, disk, saat, tarih, ağ bağlantısı.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "battery | cpu | ram | disk | time | date | network | all"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Anlik hava durumunu ozetler. Varsayilan konum Istanbul'dur. "
            "Kullanici hava durumunu, sicakligi veya yagmur durumunu sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "Sehir veya konum. Bos birakilirsa Istanbul kullanilir."
                }
            }
        }
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Apple Calendar takvimini okur. "
            "Bugun, yarin, siradaki etkinlik veya yaklasan ajandayi ozetler. "
            "Kullanici toplanti, takvim, ajanda, etkinlik veya gunluk programini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "today | tomorrow | next | agenda | week veya dogal dilde "
                        "'onumuzdeki 30 gun', '2 hafta', 'bu ay', 'gelecek ay'"
                    )
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum etkinlik sayisi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_calendar_event",
        "description": (
            "Apple Calendar takvimine yeni etkinlik ekler. "
            "Kullanici toplanti, randevu, takvime ekleme veya etkinlik olusturma isterse kullan. "
            "Baslangic tarihini gercek tarih/saat olarak ver; bitis verilmezse varsayilan sure kullanilir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Baslangic tarih/saat. ISO veya yyyy-MM-dd HH:mm formatinda."
                },
                "end_iso": {
                    "type": "STRING",
                    "description": "Bitis tarih/saat. Opsiyonel."
                },
                "location": {
                    "type": "STRING",
                    "description": "Etkinlik konumu. Opsiyonel."
                },
                "notes": {
                    "type": "STRING",
                    "description": "Etkinlik notlari. Opsiyonel."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Eklenecek takvim adi. Opsiyonel."
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "true ise tum gun etkinligi olusturur."
                }
            },
            "required": ["title", "start_iso"]
        }
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Apple Calendar takviminden etkinlik siler. "
            "Kullanici bir toplantiyi, randevuyu veya takvim kaydini silmek istediginde kullan. "
            "Ayni ada birden fazla etkinlik varsa dogru kaydi bulmak icin baslangic tarihini gercek tarih/saat olarak ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Silinecek etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ayni isimli birden fazla etkinligi ayirt etmek icin kullan."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Opsiyonel takvim adi"
                },
                "delete_all_matches": {
                    "type": "BOOLEAN",
                    "description": "true ise eslesen tum etkinlikleri siler"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "get_reminders",
        "description": (
            "Apple Animsaticilar listesini okur. "
            "Bugunku, yaklasan, geciken veya tum acik animsaticilari ozetler. "
            "Kullanici hatirlatma, animsatici, reminder veya yapilacaklar listesini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "today | upcoming | overdue | all | next"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum animsatici sayisi"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Istenirse belirli bir animsatici listesi adi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_reminder",
        "description": (
            "Apple Animsaticilar uygulamasina yeni bir animsatici ekler. "
            "Kullanici 'hatirlat', 'animsatici ekle', 'reminder kur' dediginde kullan. "
            "Goreli zaman ifadelerini bugunku tarih baglamina gore due_iso alanina ISO formatinda cevir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Animsatici basligi"
                },
                "due_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ornek: 2026-04-13T09:00 veya tum gun icin 2026-04-13"
                },
                "notes": {
                    "type": "STRING",
                    "description": "Opsiyonel not"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Opsiyonel animsatici listesi"
                },
                "priority": {
                    "type": "STRING",
                    "description": "low | medium | high"
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "Tum gun animsatici ise true"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "browser_control",
        "description": "Tarayıcıda URL açar, Google'da arama yapar veya YouTube'da ilk sonucu doğrudan oynatır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_url | search | play_youtube"},
                "url":    {"type": "STRING", "description": "Açılacak URL (open_url için)"},
                "query":  {"type": "STRING", "description": "Arama sorgusu (search veya play_youtube için)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "shell_run",
        "description": "Windows PowerShell komutu çalıştırır. Dosya yönetimi (okuma, yazma, silme, listeleme, klasör oluşturma) ve gelişmiş sistem komutları için kullanın. Örneğin: Get-ChildItem, Get-Content, Remove-Item vb.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Çalıştırılacak powershell komutu"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "play_media",
        "description": (
            "YouTube, Spotify veya Apple Music/Music uygulamasında şarkı, müzik veya video açar. "
            "Kullanıcı belirli bir platform söylerse onu kullan. "
            "Belirtmezse uygun olanı dene. "
            "Kullanıcı 'çal', 'oynat', 'aç' diyorsa autoplay=true kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Şarkı, sanatçı, albüm veya video arama ifadesi"
                },
                "provider": {
                    "type": "STRING",
                    "description": "auto | youtube | spotify | apple_music"
                },
                "autoplay": {
                    "type": "BOOLEAN",
                    "description": "true ise mümkünse doğrudan oynatır"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_youtube_channel_report",
        "description": (
            "YouTube kanalinin public istatistiklerini ve son videolarin performansini raporlar. "
            "Kullanici kanal istatistiklerini, abone sayisini, son videolarini, buyume hizini "
            "veya YouTube analizini sordugunda kullan. Bu arac Studio yerine public YouTube Data API verisini kullanir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Dogal dilde analiz istegi. Ornek: "
                        "'YouTube istatistiklerim nasil', 'son videolarimi analiz et', "
                        "'kanal buyumemi ozetle'"
                    )
                },
                "handle": {
                    "type": "STRING",
                    "description": (
                        "Opsiyonel kanal handle'i, kanal linki veya kanal ID'si. "
                        "Bos birakilirsa ayarlardaki youtube_channel_handle kullanilir."
                    )
                },
                "video_limit": {
                    "type": "NUMBER",
                    "description": "Analize dahil edilecek son video sayisi. Varsayilan 6."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_screen",
        "description": (
            "Aktif pencerenin ekran goruntusunu alip Gemini vision ile analiz eder. "
            "Kullanici ekranda ne oldugunu, bir hatayi, gorunen metni, butonlari veya pencere icerigini sordugunda kullan. "
            "Bu surum yalnizca aktif pencereyi destekler."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Kullanicinin ekranla ilgili sorusu. Ornek: 'Bu hatayi oku', 'Ekranda ne var?'"
                },
                "target": {
                    "type": "STRING",
                    "description": "Su an sadece active_window desteklenir."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_camera",
        "description": "Bilgisayar kamerasından o anki görüntüyü alır ve Gemini vision ile analiz eder. Kullanıcı 'beni görüyor musun', 'elimde ne var', 'kameraya bak' veya 'bunu nasıl yaparım (göstererek)' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Kullanıcının kameraya gösterdiği şeyle ilgili sorusu. Örn: 'Elimde ne var?', 'Bunu nasıl bağlarım?'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "click_on_screen",
        "description": "Bilgisayar ekranındaki belirli bir öğeyi bulur ve faresini hareket ettirerek tıklar. Kullanıcı 'Şuna tıkla', 'Şu butona bas', 'Masaüstündeki şu klasörü aç' (çift tıklama gerektirir) vb. dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Tıklanacak öğenin adı, metni veya açıklaması. Örn: 'Gönder butonu', 'Google Chrome simgesi'"
                },
                "double_click": {
                    "type": "BOOLEAN",
                    "description": "True ise öğeye çift tıklar (örn. klasörleri veya uygulamaları açmak için)"
                },
                "right_click": {
                    "type": "BOOLEAN",
                    "description": "True ise öğeye sağ tıklar (örn. bağlam menüsünü açmak için)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "send_arduino_command",
        "description": "Bilgisayara USB ile bağlı olan Arduino akıllı ev sistemine (röle, ışık, motor, sensör vb.) sinyal gönderir. Kullanıcı 'Işığı aç', 'LED'i yak', 'Sıcaklığı ölç' dediğinde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Gönderilecek Arduino komutu. Şimdilik desteklenenler: 'LED_ON', 'LED_OFF', 'GET_TEMP', 'PING'"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "save_memory",
        "description": "Kullanıcı hakkında önemli bilgiyi kalıcı belleğe kaydeder. İsim, tercihler, projeler vb. duyunca sessizce çağır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "identity | preferences | projects | notes"
                },
                "key":   {"type": "STRING", "description": "Kısa anahtar (örn. 'name')"},
                "value": {"type": "STRING", "description": "Değer (İngilizce)"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "delete_memory",
        "description": (
            "Kalici hafizadaki bir kaydi siler. "
            "Kullanici 'bunu hafizandan kaldir', 'unut', 'sil' gibi bir sey derse kullan. "
            "Mumkunse category ve key ile sil; emin degilsen match_text ile ilgili kaydi bulup kaldir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Kaydin kategorisi. Ornek: notes | identity | preferences | projects"
                },
                "key": {
                    "type": "STRING",
                    "description": "Silinecek anahtar. Ornek: claude_limit_refresh"
                },
                "match_text": {
                    "type": "STRING",
                    "description": "Kaydi bulmak icin kullanilacak dogal dil parcasi. Ornek: 'claude ai limit yenilenmesi'"
                }
            }
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": (
            "WhatsApp Desktop veya WhatsApp Web üzerinden mesaj taslağı açar veya mesajı gönderir. "
            "Kişi adı veya telefon numarasıyla çalışabilir. "
            "Telefon numarası verilmemişse kişi adını önce kayıtlı WhatsApp kişileri ve içe aktarılan telefon rehberinde ara. "
            "Kullanıcı 'gönder', 'yolla', 'ile', 'hemen gönder' gibi açık bir gönderme niyeti söylüyorsa "
            "ekstra onay istemeden send_now=true kullan. "
            "Yalnızca 'hazırla', 'taslak aç', 'yaz ama gönderme' diyorsa send_now=false kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {
                    "type": "STRING",
                    "description": "Kişi adı. Örn: 'Anne', 'Ahmet', 'Ece'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Uluslararası telefon numarası. Örn: +905551112233"
                },
                "message": {
                    "type": "STRING",
                    "description": "Gönderilecek mesaj içeriği"
                },
                "app_target": {
                    "type": "STRING",
                    "description": "desktop | web | auto. Varsayılan auto, tercihen desktop."
                },
                "send_now": {
                    "type": "BOOLEAN",
                    "description": "true ise sohbet açıldıktan sonra mesajı otomatik gönderir"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_whatsapp_contact",
        "description": (
            "Sık kullanılan bir WhatsApp kişisini adı ve telefon numarasıyla kalıcı belleğe kaydeder. "
            "Kullanıcı bir kişiyi 'annem', 'Ahmet', 'iş ortağım' gibi tekrar kullanılacak şekilde tanımladığında kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "Kaydedilecek kişi adı. Örn: 'Annem', 'Ahmet'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Uluslararası telefon numarası. Örn: +905551112233"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "Virgülle ayrılmış alternatif hitaplar. Örn: 'anne, annem, mom'"
                }
            },
            "required": ["display_name", "phone_number"]
        }
    },
    {
        "name": "read_notifications",
        "description": "Windows bildirim merkezinden okunmamış bildirimleri okur. Kullanıcı 'bana bildirimlerimi oku' dediğinde kullanın.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "read_file",
        "description": "Bilgisayardaki bir dosyanın içeriğini okur.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filepath": {
                    "type": "STRING",
                    "description": "Okunacak dosyanın tam veya göreli yolu. (örn: 'main.py')"
                }
            },
            "required": ["filepath"]
        }
    },
    {
        "name": "write_file",
        "description": "Bilgisayardaki bir dosyaya içerik yazar (dosya varsa tamamen üzerine yazar).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filepath": {
                    "type": "STRING",
                    "description": "Yazılacak dosyanın tam veya göreli yolu. (örn: 'main.py')"
                },
                "content": {
                    "type": "STRING",
                    "description": "Dosyaya yazılacak tüm içerik."
                }
            },
            "required": ["filepath", "content"]
        }
    },
    {
        "name": "replace_code",
        "description": "Bir dosya içindeki belirli bir kod bloğunu veya metni yenisiyle değiştirir. Hata ayıklarken veya koda ekleme yaparken kullanılır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filepath": {
                    "type": "STRING",
                    "description": "Değişiklik yapılacak dosyanın yolu. (örn: 'main.py')"
                },
                "target": {
                    "type": "STRING",
                    "description": "Dosya içinden değiştirilecek olan orijinal metin veya kod bloğu. Birebir eşleşmesi gerekir."
                },
                "replacement": {
                    "type": "STRING",
                    "description": "Hedef kısmın yerine geçecek yeni metin veya kod bloğu."
                }
            },
            "required": ["filepath", "target", "replacement"]
        }
    },
    # ── Dosya Yönetimi ─────────────────────────────────────────────────────────
    {
        "name": "file_manager",
        "description": (
            "Gelişmiş dosya ve klasör yönetimi. Listeleme, arama, kopyalama, taşıma, "
            "silme, arşivleme, büyük dosya bulma, yinelenen dosya tespiti gibi işlemler yapar. "
            "Kullanıcı 'dosyaları listele', 'klasörü arşivle', 'büyük dosyaları bul', "
            "'dosyayı taşı/kopyala/sil', 'yinelenen dosyaları bul' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "Yapılacak işlem: "
                        "list (listele) | search (ara) | copy (kopyala) | move (taşı) | "
                        "delete (sil) | create_folder (klasör oluştur) | info (bilgi) | "
                        "compress (arşivle) | extract (aç) | find_large (büyük dosyaları bul) | "
                        "find_duplicates (yinelenenleri bul) | folder_size (klasör boyutu)"
                    )
                },
                "path": {
                    "type": "STRING",
                    "description": "Hedef yol veya kısayol: masaüstü | indirilenler | belgeler | resimler | müzik | videolar | tam yol"
                },
                "src": {"type": "STRING", "description": "Kopyalama/taşıma işlemi için kaynak yol"},
                "dst": {"type": "STRING", "description": "Kopyalama/taşıma işlemi için hedef yol"},
                "pattern": {"type": "STRING", "description": "Dosya arama deseni (örn: '*.pdf', 'rapor*')"},
                "content_search": {"type": "STRING", "description": "Dosya içeriğinde aranacak metin"},
                "show_hidden": {"type": "BOOLEAN", "description": "Gizli dosyaları göster"},
                "sort_by": {"type": "STRING", "description": "name | size | date"},
                "permanent": {"type": "BOOLEAN", "description": "true = kalıcı sil, false = çöp kutusuna (varsayılan false)"},
                "paths": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Arşivlenecek dosya/klasör yolları listesi"
                },
                "output": {"type": "STRING", "description": "Arşiv çıktı dosyası yolu"},
                "archive": {"type": "STRING", "description": "Açılacak arşiv dosyası yolu"},
                "dest": {"type": "STRING", "description": "Arşiv çıkarılacak hedef klasör"},
                "min_mb": {"type": "NUMBER", "description": "Büyük dosya aramada minimum boyut (MB, varsayılan 50)"}
            },
            "required": ["action"]
        }
    },
    # ── E-posta ────────────────────────────────────────────────────────────────
    {
        "name": "send_email",
        "description": (
            "SMTP üzerinden e-posta gönderir. Dosya eki ekleyebilir. "
            "Kullanıcı 'e-posta gönder', 'mail at', 'şunu yaz ve gönder' dediğinde kullan. "
            "Gmail, Outlook, Yahoo ve özel SMTP sunucularını destekler. "
            "Ek için dosya adı veya tam yolu ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {"type": "STRING", "description": "Alıcı e-posta adresi"},
                "subject": {"type": "STRING", "description": "E-posta konusu"},
                "body": {"type": "STRING", "description": "E-posta içeriği"},
                "attachments": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Eklenecek dosyaların yolları veya adları"
                },
                "cc": {"type": "STRING", "description": "CC adresi (opsiyonel)"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "read_emails",
        "description": (
            "IMAP üzerinden gelen kutusu okur. "
            "Kullanıcı 'maillerimi oku', 'gelen kutumu kontrol et', 'okunmamış e-postalarım neler' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "folder": {"type": "STRING", "description": "INBOX | Sent | Junk (varsayılan INBOX)"},
                "count": {"type": "NUMBER", "description": "Okunacak mesaj sayısı (varsayılan 5)"},
                "unread_only": {"type": "BOOLEAN", "description": "Sadece okunmamışlar (varsayılan true)"}
            }
        }
    },
    {
        "name": "save_email_credentials",
        "description": (
            "E-posta adresini ve şifresini kalıcı olarak kaydeder. "
            "Kullanıcı 'e-posta adresimi kaydet', 'mail şifremi ayarla' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "address": {"type": "STRING", "description": "E-posta adresi"},
                "password": {"type": "STRING", "description": "E-posta şifresi veya uygulama şifresi"},
                "display_name": {"type": "STRING", "description": "Gönderici adı (opsiyonel)"}
            },
            "required": ["address", "password"]
        }
    },
    # ── WhatsApp & Bildirim Okuma ───────────────────────────────────────────────
    {
        "name": "read_whatsapp_messages",
        "description": (
            "WhatsApp Desktop uygulamasındaki okunmamış mesaj bildirimlerini okur ve sesli olarak aktarır. "
            "Kullanıcı 'WhatsApp mesajlarımı oku', 'WhatsApp'ta ne var', 'WhatsApp bildirimlerimi söyle' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "count": {"type": "NUMBER", "description": "Okunacak mesaj sayısı (varsayılan 10)"}
            }
        }
    },
    {
        "name": "get_notification_summary",
        "description": (
            "Tüm Windows bildirimlerini uygulamaya göre gruplar ve özetler. "
            "Kullanıcı 'Bildirimleri özetle', 'neler var', 'tüm bildirimleri oku' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    # ── Görev Planlayıcı ────────────────────────────────────────────────────────
    {
        "name": "create_task_plan",
        "description": (
            "Karmaşık çok adımlı bir görevi plana dönüştürür. "
            "'Masaüstümü düzenle ve eski dosyaları arşivle', 'Tüm PDF'leri bul ve bir klasöre taşı' "
            "gibi birden fazla araç gerektiren görevlerde kullan. "
            "Planı oluşturduktan sonra kullanıcıya göster ve onay iste. "
            "Onay alındıktan sonra execute_task_plan ile çalıştır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal": {"type": "STRING", "description": "Görevin amacı (kısa açıklama)"},
                "steps": {
                    "type": "ARRAY",
                    "description": "Adım listesi",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "description": {"type": "STRING", "description": "Adımın açıklaması"},
                            "tool": {"type": "STRING", "description": "Kullanılacak araç adı"},
                            "action": {"type": "STRING", "description": "Araç eylemi (file_manager için)"},
                            "args": {"type": "OBJECT", "description": "Araç argümanları"}
                        }
                    }
                }
            },
            "required": ["goal", "steps"]
        }
    },
    {
        "name": "execute_task_plan",
        "description": (
            "Mevcut planı adım adım çalıştırır. "
            "Sadece create_task_plan ile plan oluşturulduktan ve kullanıcı onay verdikten sonra kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "get_active_plan",
        "description": "Mevcut çalışan görev planının durumunu ve adımlarını gösterir.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "cancel_task",
        "description": "Aktif görevi veya planı iptal eder.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "set_volume",
        "description": "Bilgisayarın ana ses seviyesini ayarlar (0 ile 100 arasında).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level": {"type": "NUMBER", "description": "Ses seviyesi (0-100)"}
            },
            "required": ["level"]
        }
    },
    {
        "name": "set_brightness",
        "description": "Ekran parlaklığını ayarlar (0 ile 100 arasında).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "level": {"type": "NUMBER", "description": "Parlaklık seviyesi (0-100)"}
            },
            "required": ["level"]
        }
    },
    {
        "name": "set_timer",
        "description": "Geri sayım sayacı kurar. Süre dolduğunda sesli uyarı verir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "minutes": {"type": "NUMBER", "description": "Dakika"},
                "seconds": {"type": "NUMBER", "description": "Saniye"},
                "label": {"type": "STRING", "description": "Sayacın amacı veya adı (örn: Makarna)"}
            },
            "required": ["minutes", "seconds"]
        }
    },
    {
        "name": "set_alarm",
        "description": "Belirli bir saat için alarm kurar (HH:MM formatında). Zamanı geldiğinde sesli uyarı verir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "time_str": {"type": "STRING", "description": "Alarm zamanı (HH:MM formatında, örn: 14:30 veya 07:00)"},
                "label": {"type": "STRING", "description": "Alarmın amacı (örn: Toplantı)"}
            },
            "required": ["time_str"]
        }
    },
    {
        "name": "execute_code",
        "description": "Verilen Python kodunu veya bir Python dosyasını çalıştırır ve çıktısını (veya hatalarını) döndürür. Kod hatalarını ayıklamak için kullanışlıdır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "code_str": {"type": "STRING", "description": "Çalıştırılacak Python kodu (varsa)"},
                "filepath": {"type": "STRING", "description": "Çalıştırılacak Python dosyasının yolu (varsa)"}
            }
        }
    },
    {
        "name": "run_tests",
        "description": "Belirtilen dizin veya dosya üzerinde pytest çalıştırır ve test sonuçlarını döndürür.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target_path": {"type": "STRING", "description": "Test edilecek dosya veya klasör yolu (varsayılan: '.')"}
            }
        }
    },
    {
        "name": "sabah_protokolu",
        "description": "Güne başlarken günlük sabah briefing (sabah protokolü) sunumunu hazırlar ve seslendirir. Hava durumu, bilgisayar sağlığı (CPU, RAM vb.) ve Windows bildirim özetini sunar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "toggle_sentinel_mode",
        "description": "Nöbetçi Güvenlik Modunu (Sentinel Mode) açar veya kapatır. Odada hareket izlemesini aktifleştirir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "active": {"type": "BOOLEAN", "description": "true ise açar, false ise kapatır"},
                "phone_number": {"type": "STRING", "description": "Uyarı gönderilecek WhatsApp telefon numarası (varsa, örn: +905551112233)"}
            },
            "required": ["active"]
        }
    },
    {
        "name": "toggle_gesture_control",
        "description": "Jestle Medya/Müzik Kontrolü (Gesture Control) sistemini açar veya kapatır. El hareketleri (sağa, sola, yukarı, aşağı el sallama) ile Spotify ve müziği kontrol etmeyi sağlar.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "active": {"type": "BOOLEAN", "description": "true ise açar, false ise kapatır"}
            },
            "required": ["active"]
        }
    },
    {
        "name": "yuz_kaydet",
        "description": "Kullanıcının (Samet Bey) yüzünü kameradan çekerek 'profile.jpg' olarak kaydeder. Sentinel Modunda kullanıcının kendi hareketleriyle alarm tetiklenmesini engellemek için kullanılır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "ben_cikiyorum",
        "description": "Kullanıcı evden ayrılırken tetiklenen 'Ben Çıkıyorum' protokolüdür. Tarayıcıları sonlandırır, ses düzeyini düşürür, Sentinel Güvenlik modunu otomatik olarak başlatır ve WhatsApp üzerinden bildirim gönderir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "ben_geldim",
        "description": "Kullanıcı eve döndüğünde tetiklenen 'Ben Geldim' protokolüdür. Sentinel Güvenlik modunu kapatır, ses düzeyini %50'ye yükseltir ve eve dönüş durum brifingini otomatik olarak sesli okur.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "push_to_github",
        "description": "Mevcut projeyi GitHub'a yükler (commit ve push). Kullanıcı 'Projeyi GitHub'a yükle', 'kodları pushla' veya 'kodları sergile' dediğinde kullan. İsteğe bağlı olarak özel bir commit mesajı belirtebilirsin.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "commit_message": {
                    "type": "STRING",
                    "description": "Opsiyonel commit mesajı (örn: 'Yeni özellik eklendi'). Belirtilmezse varsayılan mesaj kullanılır."
                }
            }
        }
    }
]


def get_api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "")


def load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "Sen F.R.I.D.A.Y'sin — Windows'ta çalışan kişisel AI asistanı. "
            "Türkçe konuş. Kısa ve net yanıtlar ver. "
            "Araçları kullanarak görevleri tamamla, asla taklit etme."
        )


import http.server
import socket
import json
import urllib.parse
from pathlib import Path

WEB_HUD_DIR = Path(__file__).resolve().parent / "web_hud"

class WebHUDRequestHandler(http.server.BaseHTTPRequestHandler):
    live_instance = None

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            live = WebHUDRequestHandler.live_instance
            ui = live.ui if live else None
            
            status = {
                "state": live._jarvis_state if (live and hasattr(live, "_jarvis_state")) else (ui._jarvis_state if ui else "OFFLINE"),
                "paused": live.paused if (live and hasattr(live, "paused")) else False,
                "sentinel_active": False,
                "gesture_active": False,
                "user_emotion": "calm",
                "sys_stats": {
                    "cpu": 0.0,
                    "ram": 0.0,
                    "battery": 100.0
                },
                "recent_logs": []
            }
            
            if ui:
                from actions.camera_vision import is_sentinel_active, is_gesture_active
                status["sentinel_active"] = is_sentinel_active()
                status["gesture_active"] = is_gesture_active()
                status["user_emotion"] = getattr(ui, "user_emotion", "calm")
                status["sys_stats"] = getattr(ui, "_stats", status["sys_stats"])
                
                try:
                    logs_txt = ui.log_text.get("1.0", "end").strip().split("\n")
                    status["recent_logs"] = [line for line in logs_txt if line.strip()][-15:]
                except Exception:
                    pass
                    
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return
            
        elif path == "/api/video_feed":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            import cv2
            from actions.camera_vision import get_latest_frame
            import time
            
            try:
                while True:
                    frame = get_latest_frame()
                    if frame is not None:
                        ret, jpeg = cv2.imencode('.jpg', frame)
                        if ret:
                            self.wfile.write(b'--frame\r\n')
                            self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                            self.wfile.write(jpeg.tobytes())
                            self.wfile.write(b'\r\n')
                    else:
                        time.sleep(0.1)
                        continue
                    time.sleep(0.06) # ~15 FPS
            except Exception:
                return
                
        if path == "/":
            path = "/index.html"
            
        file_path = WEB_HUD_DIR / path.lstrip("/")
        
        try:
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(WEB_HUD_DIR.resolve())):
                self.send_error(403, "Access Denied")
                return
        except Exception:
            self.send_error(404, "File Not Found")
            return
            
        if resolved_path.exists() and resolved_path.is_file():
            self.send_response(200)
            ext = file_path.suffix.lower()
            content_types = {
                ".html": "text/html",
                ".css": "text/css",
                ".js": "application/javascript",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".ico": "image/x-icon"
            }
            self.send_header("Content-Type", content_types.get(ext, "application/octet-stream"))
            self.end_headers()
            with open(resolved_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        live = WebHUDRequestHandler.live_instance
        if not live:
            self.wfile.write(json.dumps({"success": False, "error": "Jarvis Live instance not found"}).encode("utf-8"))
            return
            
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if path == "/api/control":
            action = query_params.get("action", [None])[0]
            if not action:
                self.wfile.write(json.dumps({"success": False, "error": "No action specified"}).encode("utf-8"))
                return
                
            result = "Action triggered"
            loop = live._loop
            
            try:
                if action == "toggle_sentinel":
                    from actions.camera_vision import is_sentinel_active, start_sentinel_mode, stop_sentinel_mode
                    if is_sentinel_active():
                        asyncio.run_coroutine_threadsafe(loop.run_in_executor(None, stop_sentinel_mode), loop)
                        result = "Sentinel Mode disarmed."
                    else:
                        asyncio.run_coroutine_threadsafe(loop.run_in_executor(None, lambda: start_sentinel_mode(live.ui, "905537711924")), loop)
                        result = "Sentinel Mode armed."
                        
                elif action == "toggle_gesture":
                    from actions.camera_vision import is_gesture_active, start_gesture_control, stop_gesture_control
                    if is_gesture_active():
                        asyncio.run_coroutine_threadsafe(loop.run_in_executor(None, stop_gesture_control), loop)
                        result = "Gesture Control offline."
                    else:
                        asyncio.run_coroutine_threadsafe(loop.run_in_executor(None, lambda: start_gesture_control(live.ui)), loop)
                        result = "Gesture Control online."
                        
                elif action == "volume_up":
                    import pyautogui
                    pyautogui.press('volumeup')
                    result = "Volume increased."
                elif action == "volume_down":
                    import pyautogui
                    pyautogui.press('volumedown')
                    result = "Volume decreased."
                elif action == "play_pause":
                    import pyautogui
                    pyautogui.press('playpause')
                    result = "Media played/paused."
                elif action == "morning_brief":
                    asyncio.run_coroutine_threadsafe(live.execute_morning_protocol(), loop)
                    result = "Morning Protocol triggered."
                elif action == "leave_home":
                    asyncio.run_coroutine_threadsafe(live.execute_leaving_protocol(), loop)
                    result = "Leaving Home Protocol triggered."
                elif action == "return_home":
                    asyncio.run_coroutine_threadsafe(live.execute_returning_protocol(), loop)
                    result = "Returning Home Protocol triggered."
                elif action == "shutdown":
                    live.ui.root.after(0, live.ui._shutdown)
                    result = "System shutdown initiated."
                elif action.startswith("arduino_"):
                    from actions.arduino_control import send_arduino_command
                    cmd = action.replace("arduino_", "")
                    # Run in executor because it might block
                    asyncio.run_coroutine_threadsafe(loop.run_in_executor(None, lambda: send_arduino_command(cmd)), loop)
                    result = f"Arduino komutu '{cmd}' gönderildi."
                else:
                    result = f"Unknown action: {action}"
                    
                self.wfile.write(json.dumps({"success": True, "message": result}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                
        elif path == "/api/command":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                cmd = data.get("command", "").strip()
                if cmd:
                    live.ui.write_log(f"Siz (Mobil): {cmd}")
                    if live.session:
                        asyncio.run_coroutine_threadsafe(
                            live.session.send_client_content(
                                turns={"parts": [{"text": cmd}]},
                                turn_complete=True
                            ),
                            live._loop
                        )
                    self.wfile.write(json.dumps({"success": True, "message": f"Command injected: {cmd}"}).encode("utf-8"))
                else:
                    self.wfile.write(json.dumps({"success": False, "error": "Empty command"}).encode("utf-8"))
            except Exception as e:
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
                
        elif path == "/api/health_data":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                
                # Format expected by health.py
                # { "data": { "steps": 5000, ... } }
                
                health_file = Path(__file__).resolve().parent / "memory" / "health_data.json"
                health_file.parent.mkdir(exist_ok=True)
                
                with open(health_file, "w", encoding="utf-8") as f:
                    json.dump({"data": data}, f, ensure_ascii=False, indent=2)
                
                self.wfile.write(json.dumps({"success": True, "message": "Health data updated"}).encode("utf-8"))
                live.ui.write_log("SYS: Mobil cihazdan sağlık verileri güncellendi.")
            except Exception as e:
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))


class JarvisLive:
    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()

        self.ui.on_text_command  = self._on_text_command
        self.ui.on_pause_toggle  = self._on_pause_toggle
        self.ui.on_effects_state_change = self._on_effects_state_change
        self._paused             = False
        self._last_clap_time     = 0.0
        self._input_audio_buffer = []
        
        self._awaiting_rfid = True  # Başlangıçta kilitli
        self._startup_greeting_uid = None
        
        # Arduino olay dinleyicisini ayarla
        set_arduino_event_callback(self.handle_arduino_event)
        
        # Görev planlayıcı — UI log callback bağla
        set_progress_callback(lambda msg: self.ui.write_log(f"📋 {msg}"))

        # Web HUD sunucusunu başlat
        self.start_web_hud_server()

    def start_web_hud_server(self):
        def _server_thread():
            import socket
            import http.server
            import threading
            
            # Local IP bul
            local_ip = "127.0.0.1"
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except Exception:
                pass
                
            port = 8080
            WebHUDRequestHandler.live_instance = self
            
            try:
                server = http.server.ThreadingHTTPServer((local_ip, port), WebHUDRequestHandler)
                self.ui.write_log(f"SYS: Yerel Mobil HUD aktif! Tabletinizden şu adrese girin: http://{local_ip}:{port}")
                print(f"[JARVIS] 🌐 Yerel Mobil HUD Sunucusu Aktif: http://{local_ip}:{port}")
                server.serve_forever()
            except Exception as ex:
                self.ui.write_log(f"SYS: Mobil HUD sunucusu baslatilamadi: {ex}")
                print(f"[JARVIS] [HATA] Web sunucu hatasi: {ex}")
                
        threading.Thread(target=_server_thread, daemon=True).start()

    def handle_arduino_event(self, event_str: str):
        print(f"[JARVIS] 🔔 Arduino Olayı: {event_str}")
        if event_str.startswith("EVENT_RFID:"):
            uid = event_str.split(":", 1)[1].strip()
            
            if self._awaiting_rfid:
                # Sistem kilitliyken kart okutuldu, kilidi aç
                self._awaiting_rfid = False
                self._startup_greeting_uid = uid
                self.ui.write_log(f"Kilit Açıldı! Kart UID: {uid}")
                self.ui.root.after(0, self.ui.unlock_screen)
            else:
                # Sistem zaten çalışırken okutuldu (isteğe bağlı)
                if self._paused:
                    self.ui.root.after(0, self.ui._toggle_pause)
                text = f"[SİSTEM BİLDİRİMİ] Yetkili RFID kartı ({uid}) okutuldu. 'Hoş geldiniz efendim' diyerek beni karşıla."
                if self._loop and self.session:
                    asyncio.run_coroutine_threadsafe(
                        self.session.send_client_content(
                            turns={"parts": [{"text": text}]},
                            turn_complete=True
                        ),
                        self._loop
                    )

    def _on_pause_toggle(self, paused: bool):
        self._paused = paused
 
    def _activate_by_clap(self):
        self.ui.write_log("SYS: 👏 Alkış algılandı! Sistem aktif hale getiriliyor...")
        
        # Eğer ekran kilitliyse kilidi aç
        if getattr(self, "_awaiting_rfid", False):
            self._awaiting_rfid = False
            self.ui.root.after(0, self.ui.unlock_screen)
            
        # Eğer duraklatılmışsa devam ettir
        if self.ui.paused:
            self.ui._toggle_pause()
        
        # Play the iconic Start.mp3!
        self.ui.sound.play_startup()
        
        # Greet the user via a Gemini content injection
        text = "[SİSTEM BİLDİRİMİ] Samet Bey sisteme alkış ile giriş yaptı ve sistem aktif hale getirildi. Son derece karizmatik, net, vakur ve profesyonel bir siber asistan tonuyla sesli olarak 'Çevrimiçi ve hazırım, Samet Bey. Tüm sistemler aktif!' karşılaması yap. Asla 'woho', 'hey', 'hi' gibi çocuksu veya aşırı coşkulu ifadeler kullanma. Tamamen havalı, elit ve ciddi bir yapay zeka tonunu koru."
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": text}]},
                    turn_complete=True
                ),
                self._loop
            )

    def _on_effects_state_change(self, enabled: bool):
        pass

    async def _collate_briefing(self) -> str:
        loop = asyncio.get_event_loop()
        
        # 1. Hava Durumu Al
        try:
            weather_brief = await loop.run_in_executor(None, lambda: get_weather_summary(None))
        except Exception:
            weather_brief = "Hava durumu bilgisi alınamadı."
            
        # 2. Sistem Bilgilerini Al
        try:
            cpu_info = await loop.run_in_executor(None, lambda: sys_info("cpu"))
            ram_info = await loop.run_in_executor(None, lambda: sys_info("ram"))
            battery_info = await loop.run_in_executor(None, lambda: sys_info("battery"))
        except Exception:
            cpu_info, ram_info, battery_info = "", "", ""
            
        # 3. Bildirim Özetini Al
        try:
            notif_brief = await loop.run_in_executor(None, get_notification_summary)
        except Exception:
            notif_brief = "Bekleyen acil bildiriminiz bulunmuyor."
            
        return f"- Hava Durumu: {weather_brief}\n- CPU: {cpu_info}\n- RAM: {ram_info}\n- Pil: {battery_info}\n- Bildirimler: {notif_brief}"

    async def execute_morning_protocol(self) -> str:
        briefing_text = await self._collate_briefing()
        
        directive = (
            "[SİSTEM PROTOKOLÜ] Sabah Protokolü Başarıyla Tetiklendi.\n"
            "Şimdi tamamen havalı, sinematik, son derece karizmatik ve ciddi bir F.R.I.D.A.Y. ses tonuyla "
            "Samet Bey'e günlük brifingi sesli olarak oku.\n"
            "Konuşmana 'Günaydın Samet Bey. Sabah protokolünü başlattım. Tüm sistemler çevrimiçi ve stabil.' diye başla. "
            "Ardından hava durumunu, sistem sağlığını ve bildirimlerini akıcı, profesyonel bir dille özetle. "
            "Konuşmanın sonunda 'Harika bir gün geçirmenizi dilerim, efendim. Başka bir emriniz var mı?' diye sor.\n\n"
            f"VERİLER:\n{briefing_text}"
        )
        
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": directive}]},
                    turn_complete=True
                ),
                self._loop
            )
            
        return "Sabah protokolü brifingi hazırlanarak seslendiriliyor."

    async def execute_leaving_protocol(self) -> str:
        self.ui.write_log("SYS: Ben Çıkıyorum Protokolü devreye sokuldu.")
        
        # 1. Ses düzeyini kıs (%10)
        try:
            import pyautogui
            for _ in range(20):
                pyautogui.press('volumedown')
        except Exception as e:
            print(f"[LEAVING] Ses kisilamadi: {e}")
            
        # 2. Tarayıcıları kapat
        try:
            import subprocess
            subprocess.run("taskkill /F /IM chrome.exe /IM msedge.exe /IM firefox.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.ui.write_log("SYS: Aktif tarayıcı pencereleri kapatıldı.")
        except Exception as e:
            print(f"[LEAVING] Tarayici kapatma hatasi: {e}")
            
        # 3. Sentinel Modunu otomatik başlat
        from actions.camera_vision import start_sentinel_mode
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, lambda: start_sentinel_mode(self.ui, "905537711924"))
        self.ui.write_log(f"SYS: {r}")
        
        # 4. WhatsApp mesajı gönder
        from actions.whatsapp import send_whatsapp_message
        try:
            await loop.run_in_executor(None, lambda: send_whatsapp_message(
                message="Güvenlik çemberi kuruldu Samet Bey, gözünüz arkada kalmasın. Evden güvenle ayrılabilirsiniz.",
                phone_number="905537711924",
                send_now=True
            ))
        except Exception as e:
            print(f"[LEAVING] WhatsApp mesaji basarisiz: {e}")
            
        # 5. Sesli veda enjeksiyonu
        prompt = (
            "[SİSTEM PROTOKOLÜ] Samet Bey evden ayrılıyor. Ona güvenli ve harika bir yolculuk dile. "
            "Sentinel Güvenlik protokollerinin ve WhatsApp uyarı hattının aktifleştiğini, evinin güvende olduğunu belirt. "
            "Çok karizmatik, elit ve olgun bir Stark yapay zekası asistanı (F.R.I.D.A.Y.) tonuyla konuş."
        )
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": prompt}]},
                    turn_complete=True
                ),
                self._loop
            )
            
        return "Evden çıkış protokolü başarıyla kuruldu. Sentinel aktif, ses kısıldı, tarayıcılar sonlandırıldı."

    async def execute_returning_protocol(self) -> str:
        self.ui.write_log("SYS: Eve Dönüş Protokolü devreye sokuldu.")
        
        # 1. Sentinel modunu kapat
        from actions.camera_vision import stop_sentinel_mode
        loop = asyncio.get_event_loop()
        r = await loop.run_in_executor(None, stop_sentinel_mode)
        self.ui.write_log(f"SYS: {r}")
        
        # 2. Ses düzeyini orta seviyeye al (%50)
        try:
            import pyautogui
            for _ in range(15):
                pyautogui.press('volumeup')
        except Exception as e:
            print(f"[RETURNING] Ses artirilamadi: {e}")
            
        # 3. Ev brifing verilerini otomatik derle
        briefing_text = await self._collate_briefing()
        
        # 4. Sesli karşılama yapması için Gemini'a enjekte et
        prompt = (
            f"[SİSTEM PROTOKOLÜ] Samet Bey eve geri döndü! Onu büyük bir memnuniyetle, çok samimi, sıcak ve karizmatik bir "
            f"Stark yapay zekası (F.R.I.D.A.Y.) tonuyla karşıla. Eve hoş geldiniz de.\n"
            f"Ardından ona şu derlenmiş ev durum brifingini akıcı bir şekilde oku:\n\n{briefing_text}"
        )
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"parts": [{"text": prompt}]},
                    turn_complete=True
                ),
                self._loop
            )
            
        return "Eve dönüş protokolü tamamlandı. Sentinel devre dışı, hoş geldiniz brifingi seslendiriliyor."

    def _focus_ui_section_for_tool(self, tool_name: str, args: dict):
        if tool_name == "sys_info":
            query = str(args.get("query", "")).strip().lower()
            if query in {"time", "saat", "zaman", "date", "tarih"}:
                self.ui.focus_panel("time", duration_ms=5200)
            else:
                self.ui.focus_panel("system", duration_ms=5200)
        elif tool_name == "get_weather":
            self.ui.focus_panel("weather", duration_ms=5600)

    def _on_text_command(self, text: str):
        if self._paused:
            return
        self.ui.write_log(f"Siz: {text}")
        if not self._loop or not self.session:
            self.ui.write_log("ERR: F.R.I.D.A.Y bağlantısı henüz hazır değil.")
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    async def _interrupt_audio(self):
        try:
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            if self.session:
                await self.session.send_realtime_input(audio_stream_end=True)
            self.set_speaking(False)
        except Exception:
            pass


    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        else:
            self.ui.set_state("LISTENING")

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.ui.write_debug(f"{tool_name}: {short}", level="ERROR")
        self.ui.set_state("ERROR")

    @staticmethod
    def _result_looks_like_error(result) -> bool:
        text = str(result or "").strip().lower()
        if not text:
            return False
        error_markers = (
            "hata",
            "error",
            "alinamadi",
            "alınamadı",
            "bulunamadi",
            "bulunamadı",
            "acilamadi",
            "açılamadı",
            "tamamlanamadi",
            "tamamlanamadı",
            "gecersiz",
            "geçersiz",
            "izin gerekiyor",
            "izin gerekli",
            "baglanti",
            "bağlantı",
            "gerekli.",
        )
        return any(marker in text for marker in error_markers)

    @staticmethod
    def _should_play_success_sfx(tool_name: str, args: dict, result) -> bool:
        action_tools = {
            "open_app",
            "add_calendar_event",
            "add_reminder",
            "delete_calendar_event",
            "remove_calendar_event",
        }
        if tool_name in action_tools:
            return True

        if tool_name == "send_whatsapp_message":
            text = str(result or "").lower()
            if bool(args.get("send_now", False)):
                return "gönderildi" in text or "gonderildi" in text
            return False

        return False

    @staticmethod
    def _clean_transcript_text(text: str) -> tuple[str, bool]:
        raw = str(text or "")
        had_noise = False
        if CONTROL_TOKEN_RE.search(raw):
            had_noise = True
            raw = CONTROL_TOKEN_RE.sub(" ", raw)
        cleaned = []
        for ch in raw:
            if ch in "\n\r\t" or ord(ch) >= 32:
                cleaned.append(ch)
            else:
                had_noise = True
        normalized = " ".join("".join(cleaned).split())
        return normalized.strip(), had_noise

    def _build_config(self) -> types.LiveConnectConfig:
        memory  = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_p   = load_system_prompt()
        now     = datetime.datetime.now()
        time_ctx = f"[ŞU ANKİ ZAMAN]\n{now.strftime('%A, %d %B %Y — %H:%M')}\n\n"

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str + "\n\n")
        parts.append(sys_p)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=str(get_app_config_value("voice", "Charon") or "Charon")
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})
        print(f"[F.R.I.D.A.Y] 🔧 {name} {args}")
        self.ui.set_state("THINKING")

        loop   = asyncio.get_event_loop()
        result = "Tamam."
        had_exception = False

        try:
            from actions.sys_control import set_volume, get_volume
            if name == "save_memory":
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                    print(f"[Memory] 💾 {cat}/{key} = {val}")
                result = "ok"

            elif name == "delete_memory":
                result = delete_memory(
                    args.get("category", ""),
                    args.get("key", ""),
                    args.get("match_text", ""),
                )

            elif name == "get_health_data":
                from actions.health import get_health_data
                query = args.get("query", "all")
                r = await loop.run_in_executor(None, lambda: get_health_data(query))
                result = r or "Sağlık verisi alınamadı."
                # UI'da göster
                self.ui.show_health_hologram(query, result)

            elif name == "open_tablet_app":
                from actions.tablet_control import open_tablet_app
                app_name = args.get("app_name", "")
                r = await loop.run_in_executor(None, lambda: open_tablet_app(app_name))
                result = r or "İşlem başarısız."

            elif name == "close_tablet_app":
                from actions.tablet_control import close_tablet_app
                app_name = args.get("app_name", "")
                r = await loop.run_in_executor(None, lambda: close_tablet_app(app_name))
                result = r or "İşlem başarısız."

            elif name == "open_app":
                r = await loop.run_in_executor(
                    None, lambda: open_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} açıldı."

            elif name == "list_apps":
                r = await loop.run_in_executor(None, list_running_apps)
                result = r or "Çalışan uygulama listesi alınamadı."

            elif name == "kill_app":
                r = await loop.run_in_executor(
                    None, lambda: kill_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} kapatıldı."

            elif name == "sys_info":
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: sys_info(args.get("query", "all")))
                result = r or "Bilgi alındı."

            elif name == "get_weather":
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: get_weather_summary(args.get("location") or None))
                result = r or "Hava durumu bilgisi alindi."

            elif name == "get_calendar_events":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_calendar_events(
                        args.get("query", "today"),
                        int(args.get("limit", 6) or 6),
                    ),
                )
                result = r or "Takvim bilgisi alindi."

            elif name == "add_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("end_iso", ""),
                        args.get("notes", ""),
                        args.get("location", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Takvim etkinligi eklendi."

            elif name == "delete_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: delete_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("delete_all_matches", False)),
                    ),
                )
                result = r or "Takvim etkinligi silindi."

            elif name == "get_reminders":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_reminders(
                        args.get("query", "upcoming"),
                        int(args.get("limit", 8) or 8),
                        args.get("list_name", ""),
                    ),
                )
                result = r or "Animsatici bilgisi alindi."

            elif name == "add_reminder":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_reminder(
                        args.get("title", ""),
                        args.get("due_iso", ""),
                        args.get("notes", ""),
                        args.get("list_name", ""),
                        args.get("priority", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Animsatici eklendi."

            elif name == "browser_control":
                r = await loop.run_in_executor(
                    None, lambda: browser_control(
                        args.get("action"),
                        args.get("url"),
                        args.get("query")
                    ))
                result = r or "Tamam."

            elif name == "read_notifications":
                r = await loop.run_in_executor(None, read_notifications)
                result = r or "Bildirim yok."

            elif name == "shell_run":
                r = await loop.run_in_executor(
                    None, lambda: shell_run(args.get("command", "")))
                result = r or "Komut çalıştırıldı."

            elif name == "play_media":
                r = await loop.run_in_executor(
                    None,
                    lambda: play_media(
                        args.get("query", ""),
                        args.get("provider", "auto"),
                        bool(args.get("autoplay", True)),
                    ),
                )
                result = r or "Medya oynatma başlatıldı."

            elif name == "get_youtube_channel_report":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_youtube_channel_report(
                        args.get("query", "overview"),
                        args.get("handle", ""),
                        int(args.get("video_limit", 6) or 6),
                    ),
                )
                result = r or "YouTube kanal raporu alindi."

            elif name == "analyze_screen":
                r = await loop.run_in_executor(
                    None,
                    lambda: analyze_screen(
                        args.get("query", "Ekranda ne var?"),
                        args.get("target", "active_window"),
                    ),
                )
                result = r or "Ekran analizi tamamlandi."

            elif name == "analyze_camera":
                r = await loop.run_in_executor(
                    None,
                    lambda: analyze_camera(
                        args.get("query", "Önünde ne görüyorsun?")
                    ),
                )
                result = r or "Kamera analizi tamamlandi."

            elif name == "click_on_screen":
                r = await loop.run_in_executor(
                    None,
                    lambda: click_on_screen(
                        args.get("query", ""),
                        double_click=bool(args.get("double_click", False)),
                        right_click=bool(args.get("right_click", False))
                    )
                )
                result = r or "Tıklama işlemi başarılı."

            elif name == "send_arduino_command":
                r = await loop.run_in_executor(
                    None,
                    lambda: send_arduino_command(args.get("command", ""))
                )
                result = r or "Arduino komutu gönderildi."

            elif name == "send_whatsapp_message":
                r = await loop.run_in_executor(
                    None,
                    lambda: send_whatsapp_message(
                        args.get("message", ""),
                        args.get("phone_number", ""),
                        args.get("recipient_name", ""),
                        bool(args.get("send_now", False)),
                        args.get("app_target", "auto"),
                    ),
                )
                result = r or "WhatsApp işlemi tamamlandı."

            elif name == "save_whatsapp_contact":
                r = await loop.run_in_executor(
                    None,
                    lambda: save_whatsapp_contact(
                        args.get("display_name", ""),
                        args.get("phone_number", ""),
                        args.get("aliases", ""),
                    ),
                )
                result = r or "WhatsApp kişisi kaydedildi."

            elif name == "read_file":
                r = await loop.run_in_executor(
                    None, lambda: read_file(args.get("filepath", "")))
                result = r

            elif name == "write_file":
                r = await loop.run_in_executor(
                    None, lambda: write_file(args.get("filepath", ""), args.get("content", "")))
                result = r

            elif name == "replace_code":
                r = await loop.run_in_executor(
                    None, lambda: replace_code(
                        args.get("filepath", ""),
                        args.get("target", ""),
                        args.get("replacement", "")
                    ))
                result = r

            elif name == "file_manager":
                action = args.get("action", "list")
                r = await loop.run_in_executor(
                    None, lambda: file_manager(
                        action,
                        path=args.get("path", "masaüstü"),
                        src=args.get("src", ""),
                        dst=args.get("dst", ""),
                        pattern=args.get("pattern", "*"),
                        content_search=args.get("content_search", ""),
                        show_hidden=bool(args.get("show_hidden", False)),
                        sort_by=args.get("sort_by", "name"),
                        permanent=bool(args.get("permanent", False)),
                        paths=args.get("paths", []),
                        output=args.get("output", ""),
                        archive=args.get("archive", ""),
                        dest=args.get("dest", ""),
                        min_mb=float(args.get("min_mb", 50)),
                    ))
                result = r or "Dosya işlemi tamamlandı."

            elif name == "send_email":
                r = await loop.run_in_executor(
                    None, lambda: send_email(
                        to=args.get("to", ""),
                        subject=args.get("subject", ""),
                        body=args.get("body", ""),
                        attachments=args.get("attachments") or [],
                        cc=args.get("cc", ""),
                    ))
                result = r or "E-posta gönderildi."

            elif name == "read_emails":
                r = await loop.run_in_executor(
                    None, lambda: read_emails(
                        folder=args.get("folder", "INBOX"),
                        count=int(args.get("count", 5) or 5),
                        unread_only=bool(args.get("unread_only", True)),
                    ))
                result = r or "Gelen kutusu boş."

            elif name == "save_email_credentials":
                r = await loop.run_in_executor(
                    None, lambda: save_email_credentials(
                        address=args.get("address", ""),
                        password=args.get("password", ""),
                        display_name=args.get("display_name", ""),
                    ))
                result = r or "E-posta bilgileri kaydedildi."

            elif name == "read_whatsapp_messages":
                r = await loop.run_in_executor(
                    None, lambda: read_whatsapp_messages(
                        count=int(args.get("count", 10) or 10)
                    ))
                result = r or "WhatsApp mesajı bulunamadı."

            elif name == "get_notification_summary":
                r = await loop.run_in_executor(None, get_notification_summary)
                result = r or "Bildirim bulunamadı."

            elif name == "create_task_plan":
                r = await loop.run_in_executor(
                    None, lambda: create_plan(
                        goal=args.get("goal", ""),
                        steps=args.get("steps", []),
                    ))
                result = r or "Plan oluşturuldu."

            elif name == "execute_task_plan":
                # Tool executor: senkron tool çağrısı
                def _sync_tool_executor(tool_name: str, action: str, tool_args: dict) -> str:
                    import importlib
                    dispatchers = {
                        "file_manager": lambda: file_manager(action, **tool_args),
                        "shell_run":    lambda: shell_run(tool_args.get("command", "")),
                        "send_email":   lambda: send_email(**tool_args),
                        "browser_control": lambda: browser_control(
                            tool_args.get("action"),
                            tool_args.get("url"),
                            tool_args.get("query")
                        ),
                    }
                    fn = dispatchers.get(tool_name)
                    if fn:
                        return str(fn())
                    return f"Bilinmeyen araç: {tool_name}"

                r = await loop.run_in_executor(
                    None, lambda: execute_plan(_sync_tool_executor))
                result = r or "Plan tamamlandı."

            elif name == "get_active_plan":
                result = get_active_plan()

            elif name == "cancel_task":
                result = cancel_plan()

            elif name == "volume_up":
                current_vol = get_volume()
                new_vol = min(100, current_vol + 10)
                set_volume(new_vol)
                result = f"Ses %10 artırılarak %{new_vol} yapıldı."

            elif name == "volume_down":
                current_vol = get_volume()
                new_vol = max(0, current_vol - 10)
                set_volume(new_vol)
                result = f"Ses %10 azaltılarak %{new_vol} yapıldı."

            elif name == "set_volume":
                result = set_volume(args.get("level", 50))
            
            elif name == "set_brightness":
                result = await loop.run_in_executor(
                    None, lambda: set_brightness(args.get("level", 100)))

            elif name == "set_timer":
                result = await loop.run_in_executor(
                    None, lambda: set_timer(
                        int(args.get("minutes", 0)), 
                        int(args.get("seconds", 0)), 
                        args.get("label", "Zamanlayıcı")
                    ))

            elif name == "set_alarm":
                result = await loop.run_in_executor(
                    None, lambda: set_alarm(
                        args.get("time_str", "00:00"), 
                        args.get("label", "Alarm")
                    ))

            elif name == "execute_code":
                result = await loop.run_in_executor(
                    None, lambda: execute_code(
                        args.get("code_str", ""), 
                        args.get("filepath", "")
                    ))

            elif name == "run_tests":
                result = await loop.run_in_executor(
                    None, lambda: run_tests(args.get("target_path", ".")))

            elif name == "sabah_protokolu":
                result = await self.execute_morning_protocol()

            elif name == "toggle_sentinel_mode":
                active = bool(args.get("active", False))
                phone = str(args.get("phone_number", "")).strip() or "905537711924"
                if active:
                    r = await loop.run_in_executor(None, lambda: start_sentinel_mode(self.ui, phone))
                else:
                    r = await loop.run_in_executor(None, stop_sentinel_mode)
                result = r
                self.ui.write_log(f"SYS: {r}")

            elif name == "toggle_gesture_control":
                active = bool(args.get("active", False))
                if active:
                    r = await loop.run_in_executor(None, lambda: start_gesture_control(self.ui))
                else:
                    r = await loop.run_in_executor(None, stop_gesture_control)
                result = r
                self.ui.write_log(f"SYS: {r}")

            elif name == "yuz_kaydet":
                r = await loop.run_in_executor(None, lambda: register_face(self.ui))
                result = r

            elif name == "ben_cikiyorum":
                result = await self.execute_leaving_protocol()

            elif name == "ben_geldim":
                result = await self.execute_returning_protocol()

            elif name == "push_to_github":
                r = await loop.run_in_executor(
                    None,
                    lambda: push_to_github(args.get("commit_message", "Jarvis tarafından otomatik güncellendi"))
                )
                result = r

            else:
                result = f"Bilinmeyen araç: {name}"

        except Exception as e:
            result = f"Hata: {e}"
            had_exception = True
            traceback.print_exc()
            self.speak_error(name, e)

        tool_failed = self._result_looks_like_error(result)
        if tool_failed:
            if not had_exception:
                self.ui.set_state("ERROR")
        elif self._should_play_success_sfx(name, args, result):
            self.ui.play_success_sfx()

        if not tool_failed and not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] 🎤 Mikrofon başladı")
        loop = self._loop  # Use stored loop reference
        
        def audio_callback(indata, frames, callback_time, status):
            if status:
                print(f"[JARVIS] Audio input status: {status}")
            data = indata.copy()
            
            # Clap Detection
            import time
            if len(indata) > 0:
                peak = np.max(np.abs(indata))
                if peak > 20000:
                    curr = time.time()
                    if curr - getattr(self, "_last_clap_time", 0.0) > 2.0:
                        self._last_clap_time = curr
                        print(f"[JARVIS] 👏 Alkış Algılandı! Peak: {peak}")
                        if getattr(self, "_paused", False) or getattr(self, "_awaiting_rfid", False):
                            self.ui.root.after(0, self._activate_by_clap)
            
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if not jarvis_speaking and not self.ui.muted and not self._paused:
                try:
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data.tobytes(), "mime_type": "audio/pcm"}
                    )
                    # Ses izi doğrulaması için ses verisini biriktir
                    self._input_audio_buffer.append(data)
                except Exception as e:
                    print(f"[JARVIS] Audio queue error: {e}")
        
        try:
            with sd.InputStream(samplerate=SEND_SAMPLE_RATE, channels=CHANNELS, 
                               blocksize=CHUNK_SIZE, dtype='int16', callback=audio_callback):
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] ❌ Mikrofon: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] 👂 Alım başladı")
        out_buf, in_buf = [], []
        output_noise = False
        output_noise_samples = []
        try:
            while True:
                async for response in self.session.receive():
                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            raw_txt = sc.output_transcription.text.strip()
                            if raw_txt:
                                txt, had_noise = self._clean_transcript_text(raw_txt)
                                if had_noise:
                                    output_noise = True
                                    if len(output_noise_samples) < 4:
                                        output_noise_samples.append(raw_txt)
                                if txt:
                                    out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                                self.ui.mark_user_activity(True)

                        if sc.turn_complete:
                            self.set_speaking(False)

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                # --- NEW: Voice Biometrics Verification ---
                                if self._input_audio_buffer:
                                    # Biriken ses verilerini birleştir
                                    all_audio = np.concatenate(self._input_audio_buffer, axis=0).flatten()
                                    # int16'yı float32'ye normalize et (enroll_voice.py float32 kullanıyor)
                                    all_audio_float = all_audio.astype(np.float32) / 32768.0
                                    
                                    from actions.voice_auth import verify_speaker
                                    verified, similarity = verify_speaker(all_audio_float)
                                    
                                    self.ui.write_debug(f"Ses doğrulama skoru: {similarity:.2f}", level="INFO")
                                    
                                    if not verified:
                                        self.ui.write_log("SYS: Yetkisiz ses algılandı. Komut reddedildi.")
                                        await self._interrupt_audio()
                                        self._input_audio_buffer = []
                                        in_buf = []
                                        continue
                                        
                                    # Sonraki tur için temizle
                                    self._input_audio_buffer = []
                                
                                self.ui.write_log(f"Siz: {full_in}")
                                
                                # Empathy Core: Ses tonu ve duygu analizi kelime tarayıcı
                                text_lower = full_in.lower()
                                detected_emotion = None
                                
                                if any(w in text_lower for w in ["yorgun", "uykum var", "bitkin", "halsiz", "yoruldum"]):
                                    detected_emotion = "tired"
                                elif any(w in text_lower for w in ["harika", "süper", "enerjik", "bomba", "çok iyi", "heyecanlı"]):
                                    detected_emotion = "energetic"
                                elif any(w in text_lower for w in ["sinirli", "gergin", "stresli", "bıktım", "sıkıldım"]):
                                    detected_emotion = "stressed"
                                elif any(w in text_lower for w in ["sakin", "iyiyim", "rahat", "normal"]):
                                    detected_emotion = "calm"
                                    
                                if detected_emotion:
                                    self.ui.set_user_emotion(detected_emotion)
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"JARVIS: {full_out}")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Kısmen filtrelenen ses transcripti: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                            elif output_noise:
                                self.ui.write_log("ERR: JARVIS sesli yanıtını çözümlerken bir hata oluştu.")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Filtrelenen ham transcript: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                                self.ui.set_state("ERROR")
                            out_buf = []
                            output_noise = False
                            output_noise_samples = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses)

        except Exception as e:
            print(f"[JARVIS] ❌ Alım: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] 🔊 Ses çalma başladı")
        # Düşük gecikmeli playback: her chunk doğrudan output stream'e gönderilir
        try:
            with sd.RawOutputStream(
                samplerate=RECV_SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                blocksize=512,  # Küçük blok = düşük latency
            ) as stream:
                while True:
                    chunk = await self.audio_in_queue.get()
                    self.set_speaking(True)
                    if isinstance(chunk, (bytes, bytearray)):
                        stream.write(chunk)
                    elif isinstance(chunk, np.ndarray):
                        stream.write(chunk.astype(np.int16).tobytes())
        except Exception as e:
            print(f"[JARVIS] ❌ Ses: {e}")
            raise
        finally:
            self.set_speaking(False)

    async def run(self):
        self._loop = asyncio.get_running_loop()
        client = genai.Client(
            api_key=get_api_key(),
            http_options={"api_version": "v1alpha"}
        )

        # Başlangıçta RFID okutulmasını bekle
        if getattr(self, '_awaiting_rfid', False):
            print("[JARVIS] 🔒 SİSTEM KİLİTLİ. Devam etmek için RFID kartınızı okutun...")
            self.ui.write_log("SYS: SİSTEM KİLİTLİ. Lütfen yetkili RFID kartınızı okutun.")
            self.ui.set_state("PAUSED")
            self.ui.root.after(0, self.ui.show_lock_screen)
            while self._awaiting_rfid:
                await asyncio.sleep(0.5)
            # Kilit açıldı
            self.ui.set_state("THINKING")

        while True:
            # Duraklatılmışsa bağlanma, bekle
            if getattr(self, '_paused', False):
                await asyncio.sleep(1)
                continue

            try:
                print("[JARVIS] 🔌 Bağlanıyor...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[JARVIS] ✅ Bağlandı.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: Friday hazır dinliyorum...")

                    # Eğer startup greeting bekliyorsa gönder
                    if getattr(self, '_startup_greeting_uid', None):
                        uid = self._startup_greeting_uid
                        self._startup_greeting_uid = None
                        text = f"[SİSTEM BİLDİRİMİ] Yetkili RFID kartı ({uid}) okutuldu. Sistemi aktif ettim. Lütfen 'Hoş geldiniz efendim, sizin için ne yapabilirim?' diyerek beni karşıla."
                        # Hemen gemini'ye yolluyoruz
                        await self.session.send_client_content(
                            turns={"parts": [{"text": text}]},
                            turn_complete=True
                        )

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())

            except Exception as e:
                print(f"[JARVIS] ⚠️ {e}")
                traceback.print_exc()
                self.set_speaking(False)
                self.ui.write_log(f"ERR: JARVIS baglantisi kesildi veya internete ulasilamiyor — {e}")
                self.ui.set_state("ERROR")
                print("[JARVIS] 🔄 3 saniyede yeniden bağlanıyor...")
                await asyncio.sleep(3)


def main():
    import atexit
    lock_file = Path(__file__).resolve().parent / "friday.lock"

    def cleanup():
        if lock_file.exists():
            try:
                lock_file.unlink()
                print("[JARVIS] 🧹 Kilit dosyasi silindi.")
            except Exception as e:
                print(f"[JARVIS] ⚠️ Kilit dosyasi silinemedi: {e}")

    try:
        lock_file.write_text(str(os.getpid()), encoding="utf-8")
        atexit.register(cleanup)
    except Exception:
        pass

    if os.environ.get("TERM_PROGRAM") == "vscode":
        print("[JARVIS] VS Code icinden baslatildi.")

    ui = JarvisUI()

    def runner():
        ui.wait_for_api_key()
        jarvis = JarvisLive(ui)
        
        # Bipass callback'ini bağla (Arayüzdeki "KARTIM YOK" butonu için)
        def do_bypass():
            jarvis._awaiting_rfid = False
            jarvis._startup_greeting_uid = "BYPASS_UI_9999"
        ui.on_rfid_bypass = do_bypass
        
        init_arduino()
        try:
            asyncio.run(jarvis.run())
        except KeyboardInterrupt:
            print("\n🔴 Kapatılıyor...")

    threading.Thread(target=runner, daemon=True).start()
    try:
        ui.root.mainloop()
    except KeyboardInterrupt:
        print("\n🔴 Kapatılıyor...")
    except Exception as e:
        print(f"\n🔴 Ana dongu hatasi: {e}")


if __name__ == "__main__":
    main()
