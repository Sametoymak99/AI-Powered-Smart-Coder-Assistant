import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from actions.arduino_control import send_arduino_command, _connect_arduino

print("Bağlanıyor...")
ok, msg = _connect_arduino()
print(f"Bağlantı: {ok}, {msg}")

print("Komut gönderiliyor: GET_TEMP")
res = send_arduino_command("GET_TEMP")
print(f"Cevap: {res}")
