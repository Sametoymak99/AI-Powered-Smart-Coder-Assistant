import time
import serial
import serial.tools.list_ports
import threading
import queue

_arduino_serial = None
_response_queue = queue.Queue()
_listener_thread = None
_on_event_callback = None
_is_connected = False

def set_arduino_event_callback(callback):
    """Arduino'dan gelen asenkron olayları dinlemek için callback ayarlar."""
    global _on_event_callback
    _on_event_callback = callback

def _serial_listener():
    global _arduino_serial, _is_connected
    while _is_connected and _arduino_serial and _arduino_serial.is_open:
        try:
            if _arduino_serial.in_waiting > 0:
                line = _arduino_serial.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Olay (Event) kontrolü
                if line.startswith("EVENT_"):
                    if _on_event_callback:
                        _on_event_callback(line)
                elif line.startswith("Kart ID:"):
                    # Kullanıcının kendi yüklediği kodu destekle
                    uid = line.replace("Kart ID:", "").strip()
                    if _on_event_callback:
                        _on_event_callback(f"EVENT_RFID:{uid}")
                else:
                    # Normal komut yanıtı (Eğer FRIDAY_READY gibi loglar değilse)
                    if line != "FRIDAY_READY" and line != "Kart Okundu!":
                        _response_queue.put(line)
            else:
                time.sleep(0.05)
        except Exception as e:
            print(f"[Arduino] Dinleyici hatası: {e}")
            break

def _connect_arduino():
    global _arduino_serial, _listener_thread, _is_connected
    
    # Zaten bağlıysa ve açıksa
    if _arduino_serial and _arduino_serial.is_open:
        return True, ""

    # Portları tara
    ports = serial.tools.list_ports.comports()
    arduino_port = None
    
    # Basit bir eşleştirme (CH340 veya Arduino kelimesi geçiyorsa)
    for port in ports:
        desc = port.description.lower()
        if "arduino" in desc or "ch340" in desc or "usb-serial" in desc or "usb serial" in desc:
            arduino_port = port.device
            break
            
    # Eğer özel bir açıklama bulunamadıysa ilk uygun portu dene (riskli ama genelde çalışır)
    if not arduino_port and len(ports) > 0:
        for port in ports:
            # COM portları deneyebilir
            if "COM" in port.device:
                arduino_port = port.device
                break

    if not arduino_port:
        return False, "Sisteme bağlı bir Arduino veya Seri Port cihazı bulunamadı."

    try:
        # Arduino Uno / Nano için genelde 9600 baud uygundur
        _arduino_serial = serial.Serial(port=arduino_port, baudrate=9600, timeout=2)
        # Seri port açıldıktan sonra Arduino resetlenir, biraz beklemek gerekir
        time.sleep(2)
        
        _is_connected = True
        
        # Dinleyici iş parçacığını başlat
        _listener_thread = threading.Thread(target=_serial_listener, daemon=True)
        _listener_thread.start()
        
        return True, f"Arduino {arduino_port} üzerinden bağlandı."
    except Exception as e:
        _is_connected = False
        return False, f"Arduino bağlantısı başarısız oldu: {e}"

def init_arduino():
    """Sistem başlarken Arduino bağlantısını zorla başlatır."""
    _connect_arduino()

def send_arduino_command(command: str) -> str:
    """
    Arduino'ya komut yollar ve cevabını okur.
    Örn: "LED_ON", "LED_OFF", "GET_TEMP"
    """
    global _arduino_serial, _response_queue
    command = command.strip().upper()
    
    ok, msg = _connect_arduino()
    if not ok:
        return msg

    try:
        # Kuyruktaki eski (istenmeyen) yanıtları temizle
        while not _response_queue.empty():
            try:
                _response_queue.get_nowait()
            except queue.Empty:
                break
                
        # Komutu gönder
        _arduino_serial.write((command + "\n").encode('utf-8'))
        
        # Cevabı bekle
        try:
            # 5 saniye zaman aşımı ile kuyruktan cevabı bekle
            response = _response_queue.get(timeout=5.0)
            
            if not response:
                return f"Komut gönderildi ({command}) ancak Arduino'dan cevap alınamadı."
                
            return f"Arduino Cevabı: {response}"
            
        except queue.Empty:
            return f"Komut gönderildi ({command}) ancak belirtilen sürede (5s) Arduino'dan cevap alınamadı."
            
    except Exception as e:
        # Hata olursa portu kapat
        if _arduino_serial and _arduino_serial.is_open:
            _arduino_serial.close()
        global _is_connected
        _is_connected = False
        _arduino_serial = None
        return f"Komut gönderilirken hata oluştu: {e}"
