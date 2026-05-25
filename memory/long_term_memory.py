import sqlite3
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("LongTermMemory")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "memory" / "friday_memory.db"

class LongTermMemory:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LongTermMemory, cls).__new__(cls)
                cls._instance._init_db()
            return cls._instance

    def _init_db(self):
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.conn_lock = threading.Lock()
        
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE), check_same_thread=False)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    command TEXT,
                    result TEXT,
                    agent TEXT,
                    duration_ms INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_data TEXT,
                    confidence REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour_of_day INTEGER,
                    day_of_week INTEGER,
                    common_commands TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()

        # Start background pattern extractor thread
        self.running = True
        self.extractor_thread = threading.Thread(target=self._extractor_loop, daemon=True)
        self.extractor_thread.start()

    def _extractor_loop(self):
        while self.running:
            try:
                self._extract_patterns()
            except Exception as e:
                logger.error(f"Error extracting patterns: {e}")
            time.sleep(1800) # 30 mins

    def log_interaction(self, command: str, result: str, agent: str = "general", duration_ms: int = 0):
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interactions (command, result, agent, duration_ms)
                VALUES (?, ?, ?, ?)
            """, (command, result, agent, duration_ms))
            conn.commit()
            conn.close()
            logger.info("Logged interaction in long term database.")

    def get_patterns(self) -> List[Dict[str, Any]]:
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patterns ORDER BY confidence DESC")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def learn_pattern(self, pattern_type: str, pattern_data: str, confidence: float):
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM patterns WHERE pattern_type = ? AND pattern_data = ?
            """, (pattern_type, pattern_data))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE patterns SET confidence = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?
                """, (confidence, row[0]))
            else:
                cursor.execute("""
                    INSERT INTO patterns (pattern_type, pattern_data, confidence)
                    VALUES (?, ?, ?)
                """, (pattern_type, pattern_data, confidence))
            conn.commit()
            conn.close()

    def get_context_summary(self, last_n: int = 20) -> str:
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, result FROM interactions ORDER BY timestamp DESC LIMIT ?
            """, (last_n,))
            rows = cursor.fetchall()
            conn.close()
        
        if not rows:
            return "Konuşma geçmişi henüz boş."
            
        summary_lines = []
        for cmd, res in reversed(rows):
            # Keep command and result summary small
            cmd_trunc = cmd[:60] + "..." if len(cmd) > 60 else cmd
            res_trunc = res[:80] + "..." if len(res) > 80 else res
            summary_lines.append(f"Kullanıcı: {cmd_trunc} -> F.R.I.D.A.Y.: {res_trunc}")
            
        return "\n".join(summary_lines)

    def search_history(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM interactions 
                WHERE command LIKE ? OR result LIKE ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]

    def get_daily_stats(self) -> Dict[str, Any]:
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*), AVG(duration_ms) FROM interactions 
                WHERE date(timestamp) = date('now')
            """)
            cnt, avg_dur = cursor.fetchone()
            conn.close()
        return {
            "interaction_count": cnt or 0,
            "avg_response_time_ms": int(avg_dur or 0)
        }

    def _extract_patterns(self):
        # Scan interactions and learn time-based habits
        with self.conn_lock:
            conn = sqlite3.connect(str(DB_FILE))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, strftime('%H', timestamp) as hr 
                FROM interactions 
                WHERE timestamp >= datetime('now', '-7 days')
            """)
            rows = cursor.fetchall()
            conn.close()
            
        if not rows:
            return
            
        # Compile hours vs command types
        hour_map = {}
        for cmd, hr in rows:
            hr_val = int(hr)
            if hr_val not in hour_map:
                hour_map[hr_val] = []
            hour_map[hr_val].append(cmd)
            
        for hr, cmds in hour_map.items():
            if len(cmds) >= 3:
                # Find common keyword or pattern
                # Örn: 'kod', 'yaz', 'run', 'execute'
                for kw in ["kod", "python", "arduino", "müzik", "whatsapp", "kamera"]:
                    matches = [c for c in cmds if kw in c.lower()]
                    if len(matches) >= 3:
                        confidence = min(1.0, len(matches) / len(cmds))
                        habit_text = f"Kullanıcı genelde {hr}:00 saatlerinde '{kw}' komutları çalıştırıyor."
                        self.learn_pattern("time_habit", habit_text, confidence)
                        logger.info(f"Learned pattern: {habit_text} (confidence={confidence})")

long_term_memory = LongTermMemory()
