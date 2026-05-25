import socket
import hashlib
import base64
import threading
import json
import logging
import struct
from typing import List, Dict, Any, Callable

logger = logging.getLogger("NexusWSServer")

class NexusWSServer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(NexusWSServer, cls).__new__(cls)
                cls._instance._init_server()
            return cls._instance

    def _init_server(self):
        self.clients: List[socket.socket] = []
        self.port = 8765
        self.running = False
        self.handlers: Dict[str, Callable[[Dict[str, Any], socket.socket], None]] = {}
        self.server_socket = None

    def register_handler(self, msg_type: str, callback: Callable[[Dict[str, Any], socket.socket], None]):
        self.handlers[msg_type] = callback

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._listen_loop, name="WS-ListenLoop", daemon=True).start()
        logger.info(f"NEXUS WS Server starting on port {self.port}...")

    def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message, ensure_ascii=False)
        frame = self._make_text_frame(payload)
        
        bad_clients = []
        for client in list(self.clients):
            try:
                client.sendall(frame)
            except Exception:
                bad_clients.append(client)
                
        for bc in bad_clients:
            if bc in self.clients:
                self.clients.remove(bc)

    def _make_text_frame(self, text: str) -> bytes:
        data = text.encode('utf-8')
        length = len(data)
        frame = bytearray()
        
        # Opcode 1 for text frame, FIN bit set (0x80)
        frame.append(0x81)
        
        if length <= 125:
            frame.append(length)
        elif length <= 65535:
            frame.append(126)
            frame.extend(struct.pack("!H", length))
        else:
            frame.append(127)
            frame.extend(struct.pack("!Q", length))
            
        frame.extend(data)
        return bytes(frame)

    def _listen_loop(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(("0.0.0.0", self.port))
            self.server_socket.listen(5)
        except Exception as e:
            logger.error(f"Could not bind/listen WS server: {e}")
            self.running = False
            return

        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                threading.Thread(target=self._handle_client, args=(client_sock,), daemon=True).start()
            except Exception:
                break

    def _handle_client(self, client_sock: socket.socket):
        # 1. Handshake
        try:
            request = client_sock.recv(4096).decode('utf-8', errors='ignore')
            if "Upgrade: websocket" not in request:
                client_sock.close()
                return
                
            # Extract Sec-WebSocket-Key
            key = None
            for line in request.split("\r\n"):
                if line.lower().startswith("sec-websocket-key:"):
                    key = line.split(":", 1)[1].strip()
                    break
                    
            if not key:
                client_sock.close()
                return
                
            # Handshake response
            guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept_val = base64.b64encode(hashlib.sha1((key + guid).encode('utf-8')).digest()).decode('utf-8')
            
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
            )
            client_sock.sendall(response.encode('utf-8'))
            self.clients.append(client_sock)
            logger.info("WS Client connected and handshaked.")
        except Exception as e:
            logger.error(f"WS Handshake failed: {e}")
            client_sock.close()
            return

        # 2. Read Loop
        while self.running:
            try:
                # Read header
                header = client_sock.recv(2)
                if not header or len(header) < 2:
                    break
                    
                fin_opcode = header[0]
                mask_payload_len = header[1]
                
                # Check FIN bit & Opcode
                opcode = fin_opcode & 0x0F
                if opcode == 0x8: # Connection close
                    break
                    
                has_mask = (mask_payload_len & 0x80) != 0
                payload_len = mask_payload_len & 0x7F
                
                if payload_len == 126:
                    len_bytes = client_sock.recv(2)
                    payload_len = struct.unpack("!H", len_bytes)[0]
                elif payload_len == 127:
                    len_bytes = client_sock.recv(8)
                    payload_len = struct.unpack("!Q", len_bytes)[0]
                    
                mask = b""
                if has_mask:
                    mask = client_sock.recv(4)
                    
                # Read payload
                payload = bytearray()
                remaining = payload_len
                while remaining > 0:
                    chunk = client_sock.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    payload.extend(chunk)
                    remaining -= len(chunk)
                    
                if len(payload) < payload_len:
                    break
                    
                # Unmask payload
                if has_mask:
                    unmasked = bytearray(len(payload))
                    for i in range(len(payload)):
                        unmasked[i] = payload[i] ^ mask[i % 4]
                    decoded = unmasked.decode('utf-8', errors='ignore')
                else:
                    decoded = payload.decode('utf-8', errors='ignore')
                    
                # Process message
                try:
                    msg = json.loads(decoded)
                    msg_type = msg.get("type")
                    if msg_type in self.handlers:
                        self.handlers[msg_type](msg, client_sock)
                except Exception as ex:
                    logger.error(f"Error handling WS msg: {ex}")
                    
            except Exception:
                break
                
        if client_sock in self.clients:
            self.clients.remove(client_sock)
        client_sock.close()
        logger.info("WS Client disconnected.")

nexus_ws_server = NexusWSServer()
