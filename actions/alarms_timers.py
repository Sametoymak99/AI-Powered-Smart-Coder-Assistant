"""
Zaman Yönetimi: Sayaç ve Alarmlar
"""
import threading
import time
import datetime
import winsound

def _play_alarm_sound():
    for _ in range(5):
        winsound.Beep(1000, 400)
        time.sleep(0.1)
        winsound.Beep(1500, 400)
        time.sleep(0.5)

def set_timer(minutes: int, seconds: int, label: str = "Zamanlayıcı") -> str:
    total_seconds = minutes * 60 + seconds
    if total_seconds <= 0:
        return "Süre 0'dan büyük olmalıdır."
    
    def timer_thread():
        time.sleep(total_seconds)
        _play_alarm_sound()
        # Opsiyonel: Bildirim de gösterilebilir (Windows Toast)
        try:
            from actions.notifications import WPN_DB # Sadece bağımlılık olarak kullanmıyoruz
            # Powershell ile toast notification gönder
            import subprocess
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
            $template = "<toast><visual><binding template='ToastText02'><text id='1'>Zamanlayıcı Doldu!</text><text id='2'>{label}</text></binding></visual></toast>"
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("F.R.I.D.A.Y").Show($toast)
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
            
    t = threading.Thread(target=timer_thread, daemon=True)
    t.start()
    
    return f"'{label}' için {minutes} dakika {seconds} saniye sayacı başlatıldı."

def set_alarm(time_str: str, label: str = "Alarm") -> str:
    try:
        now = datetime.datetime.now()
        target_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        target_dt = datetime.datetime.combine(now.date(), target_time)
        
        if target_dt <= now:
            target_dt += datetime.timedelta(days=1)
            
        wait_seconds = (target_dt - now).total_seconds()
        
        def alarm_thread():
            time.sleep(wait_seconds)
            _play_alarm_sound()
            try:
                import subprocess
                ps_script = f"""
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
                $template = "<toast><visual><binding template='ToastText02'><text id='1'>Alarm Zamanı!</text><text id='2'>{label}</text></binding></visual></toast>"
                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = New-Object Windows.UI.Notifications.ToastNotification $xml
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("F.R.I.D.A.Y").Show($toast)
                """
                subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception:
                pass
            
        t = threading.Thread(target=alarm_thread, daemon=True)
        t.start()
        
        return f"'{label}' adlı alarm {target_dt.strftime('%H:%M')} saatine kuruldu."
    except Exception as e:
        return f"Alarm kurulamadı, zaman formatı 'HH:MM' olmalıdır. Hata: {e}"
