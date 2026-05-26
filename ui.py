"""
F.R.I.D.A.Y macOS — UI v3
Concentric teal rings · Segmented arcs
Alp Ünlü tarafından yapılmıştır — @alppunlu
"""

import os, time, math, random, signal, threading
import subprocess
import tkinter as tk
from collections import deque
from pathlib import Path
import psutil
from PIL import Image, ImageTk

from app_config import has_gemini_api_key, load_app_config, save_app_config
from actions.weather import get_weather_summary

BASE_DIR = Path(__file__).resolve().parent

SYSTEM_NAME = "F.R.I.D.A.Y"
MODEL_BADGE = "VOICE CORE · FRIDAY"

# ── Tema sistemi ─────────────────────────────────────────────────────────────
THEMES = {
    "dark": {
        "C_BG":     "#090a0f",
        "C_PRI":    "#6366f1", # Indigo
        "C_ORG":    "#a855f7", # Violet
        "C_ORG2":   "#06b6d4", # Cyan
        "C_MID":    "#1e1b4b", # Koyu Indigo
        "C_DIM":    "#1e293b", # Slate
        "C_DIMMER": "#0f172a", # Slate Koyu
        "C_TEXT":   "#f8fafc", # Beyazımsı
        "C_PANEL":  "#0f172a", # Panel
        "C_GREEN":  "#10b981", # Modern Yeşil
        "C_RED":    "#ef4444", # Modern Kırmızı
        "C_MUTED":  "#64748b", # Muted Slate
        "C_BLUE":   "#3b82f6", # Modern Mavi
        "C_GOLD":   "#f59e0b", # Modern Sarı/Altın
        "ORB_COLORS": {
            "LISTENING":    (99, 102, 241), # Indigo
            "SPEAKING":     (168, 85, 247), # Violet
            "THINKING":     (6, 182, 212), # Cyan
            "MUTED":        (100, 116, 139),
            "PAUSED":       (30, 41, 59),
            "ERROR":        (239, 68, 68),
            "INITIALISING": (239, 68, 68),
        },
    },
    "light": {
        "C_BG":     "#f8fafc", # Kirli beyaz / Off-white
        "C_PRI":    "#4f46e5", # Indigo (Ana renk)
        "C_ORG":    "#9333ea", # Purple
        "C_ORG2":   "#06b6d4", # Cyan
        "C_MID":    "#e2e8f0", # Border / Divider
        "C_DIM":    "#f1f5f9", # Kart arka planı
        "C_DIMMER": "#e2e8f0", # Daha koyu gri
        "C_TEXT":   "#0f172a", # Koyu Slate (Metin)
        "C_PANEL":  "#ffffff", # Saf beyaz panel
        "C_GREEN":  "#10b981", # Yeşil
        "C_RED":    "#ef4444", # Kırmızı
        "C_MUTED":  "#94a3b8", # Silik metin
        "C_BLUE":   "#2563eb", # Mavi
        "C_GOLD":   "#ca8a04", # Altın/Sarı
        "ORB_COLORS": {
            "LISTENING":    (79, 70, 229), # Indigo
            "SPEAKING":     (147, 51, 234), # Purple
            "THINKING":     (6, 182, 212), # Cyan
            "MUTED":        (148, 163, 184),
            "PAUSED":       (226, 232, 240),
            "ERROR":        (239, 68, 68),
            "INITIALISING": (239, 68, 68),
        },
    },
    "nexus": {
        "C_BG":     "#050814", # Koyu Gece Mavisi
        "C_PRI":    "#bd00ff", # Neon Violet
        "C_ORG":    "#00e5ff", # Neon Cyan
        "C_ORG2":   "#ff0055", # Hot Pink
        "C_MID":    "#151b30", # Koyu Mavi Çerçeve
        "C_DIM":    "#0d1326", # Slate / Mavi Tonu
        "C_DIMMER": "#080c1b", # Çok Koyu Panel
        "C_TEXT":   "#ffffff", # Saf Beyaz
        "C_PANEL":  "#080c1b", # Panel Arkaplanı
        "C_GREEN":  "#00ff88", # Cyberpunk Yeşil
        "C_RED":    "#ff2d55", # Cyberpunk Kırmızı
        "C_MUTED":  "#5b6e9c", # Muted Mavi-Slate
        "C_BLUE":   "#00a2ff", # Parlak Mavi
        "C_GOLD":   "#ffbb00", # Altın
        "ORB_COLORS": {
            "LISTENING":    (0, 229, 255), # Neon Cyan
            "SPEAKING":     (189, 0, 255), # Neon Violet
            "THINKING":     (255, 0, 85), # Hot Pink
            "MUTED":        (91, 110, 156),
            "PAUSED":       (13, 19, 38),
            "ERROR":        (255, 45, 85),
            "INITIALISING": (255, 45, 85),
        },
    },
}

def _load_theme_globals(theme_name: str):
    """Aktif temayı modül genelinde günceller."""
    import sys
    module = sys.modules[__name__]
    t = THEMES[theme_name]
    for k, v in t.items():
        if k != "ORB_COLORS":
            setattr(module, k, v)
    global ORB_COLORS
    ORB_COLORS = t["ORB_COLORS"]

# ── Renk paleti (başlangıç: light) ────────────────────────────────────────────
C_BG      = THEMES["dark"]["C_BG"]
C_PRI     = THEMES["dark"]["C_PRI"]
C_ORG     = THEMES["dark"]["C_ORG"]
C_ORG2    = THEMES["dark"]["C_ORG2"]
C_MID     = THEMES["dark"]["C_MID"]
C_DIM     = THEMES["dark"]["C_DIM"]
C_DIMMER  = THEMES["dark"]["C_DIMMER"]
C_TEXT    = THEMES["dark"]["C_TEXT"]
C_PANEL   = THEMES["dark"]["C_PANEL"]
C_GREEN   = THEMES["dark"]["C_GREEN"]
C_RED     = THEMES["dark"]["C_RED"]
C_MUTED   = THEMES["dark"]["C_MUTED"]
C_BLUE    = THEMES["dark"]["C_BLUE"]
C_GOLD    = THEMES["dark"]["C_GOLD"]

# Orb durum renkleri
ORB_COLORS = THEMES["dark"]["ORB_COLORS"]

STATE_HEX_COLORS = {
    "LISTENING": C_GREEN,
    "SPEAKING":  C_BLUE,
    "THINKING":  C_GOLD,
    "INITIALISING": C_RED,
    "ERROR":     C_RED,
}

W_TARGET = 2200
H_TARGET = 1320
LEFT_W_T = 360
RIGHT_W_T = 410
HDR_H    = 72
FOOTER_H = 26
INPUT_H  = 34
CONTROL_H = 146

VOICES = ["Charon", "Puck", "Aoede", "Kore", "Fenrir", "Leda", "Orus", "Zephyr"]

# ── Font sistemi ─────────────────────────────────────────────────────────────
# Segoe UI, Windows sistemlerinde gövde metinleri ve butonlar için en net ve elit 
# okuma deneyimini sunar. Grift ise başlıklar için fütüristik yapıyı korur.
FONT_BODY_FAMILY = "Segoe UI"
FONT_DISPLAY_FAMILY = "Grift Extra Bold"


def font_body(size: int):
    return (FONT_BODY_FAMILY, size)


def font_body_bold(size: int):
    return (FONT_BODY_FAMILY, size, "bold")


def font_display(size: int):
    return (FONT_DISPLAY_FAMILY, size)


STATE_HEX_COLORS = {
    "LISTENING": C_GREEN,
    "SPEAKING": C_BLUE,
    "THINKING": C_GOLD,
    "INITIALISING": C_RED,
    "ERROR": C_RED,
}


# ── SoundManager ─────────────────────────────────────────────────────────────
import subprocess as _sp

def _resolve_sfx_dir() -> Path:
    return BASE_DIR / "SFX"


_SFX_DIR = _resolve_sfx_dir()
_HUD_FILE = _SFX_DIR / "HUD.mp3"
_START_FILE = _SFX_DIR / "Start.mp3"
_THINK_FILE = _SFX_DIR / "Think.mp3"
_DONE_FILE = _SFX_DIR / "Done.mp3"
_ERROR_FILE = _SFX_DIR / "Error.mp3"
_POWER_UP_FILE = _SFX_DIR / "power_up.mp3"
_JARVIS_LINES_FILE = _SFX_DIR / "Jarvis_lines.mp3"


class SoundManager:
    def __init__(self):
        self._enabled = True
        self._ambient_proc = None
        self._volume = 0.20
        self._ambient_stop = None
        self._ambient_thread = None
        self._foreground_proc = None
        self._foreground_stop = None
        self._foreground_thread = None
        self._foreground_tag = ""
        self._all_sound_procs = set()
        self._lock = threading.RLock()

    @staticmethod
    def _terminate_process(proc):
        if not proc:
            return
        if proc.poll() is not None:
            return
        killed_group = False
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            killed_group = True
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass
        try:
            proc.wait(timeout=0.6)
        except Exception:
            try:
                if killed_group:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
                proc.wait(timeout=0.3)
            except Exception:
                pass

    def _start_afplay(self, path: Path, volume: float):
        import platform
        if platform.system() == "Windows":
            import sys
            abs_path = path.resolve()
            vol_1000 = int(volume * 1000)
            py_code = (
                f"import ctypes, time; "
                f"ctypes.windll.winmm.mciSendStringW('open \"{abs_path.as_posix()}\" type mpegvideo alias s', None, 0, 0); "
                f"ctypes.windll.winmm.mciSendStringW('setaudio s volume to {vol_1000}', None, 0, 0); "
                f"ctypes.windll.winmm.mciSendStringW('play s', None, 0, 0); "
                f"time.sleep(360)"
            )
            proc = _sp.Popen(
                [sys.executable, "-c", py_code],
                stdout=_sp.DEVNULL,
                stderr=_sp.DEVNULL,
                creationflags=_sp.CREATE_NO_WINDOW if hasattr(_sp, "CREATE_NO_WINDOW") else 0
            )
        else:
            proc = _sp.Popen(
                ["afplay", "-v", f"{volume:.2f}", str(path)],
                stdout=_sp.DEVNULL,
                stderr=_sp.DEVNULL,
                start_new_session=True,
            )
        with self._lock:
            self._all_sound_procs.add(proc)
        return proc

    def _forget_process(self, proc):
        if not proc:
            return
        with self._lock:
            self._all_sound_procs.discard(proc)

    def start_ambient(self):
        if not _HUD_FILE.exists():
            return
        with self._lock:
            if not self._enabled:
                return
            if self._foreground_proc and self._foreground_proc.poll() is None:
                return
            if self._ambient_thread and self._ambient_thread.is_alive():
                return
            stop_event = threading.Event()
            worker = threading.Thread(
                target=self._loop_ambient,
                args=(stop_event,),
                daemon=True,
            )
            self._ambient_stop = stop_event
            self._ambient_thread = worker
        worker.start()

    def _loop_ambient(self, stop_event: threading.Event):
        while not stop_event.is_set():
            with self._lock:
                if not self._enabled or self._ambient_stop is not stop_event:
                    break
                volume = self._volume
            try:
                proc = self._start_afplay(_HUD_FILE, volume)
            except Exception:
                break

            with self._lock:
                if self._ambient_stop is not stop_event or not self._enabled:
                    self._terminate_process(proc)
                    self._forget_process(proc)
                    break
                self._ambient_proc = proc

            while proc.poll() is None and not stop_event.wait(0.2):
                pass

            if stop_event.is_set():
                self._terminate_process(proc)

            with self._lock:
                if self._ambient_proc is proc:
                    self._ambient_proc = None
            if proc.poll() is not None:
                self._forget_process(proc)

            if stop_event.is_set():
                break
            time.sleep(0.2)

        with self._lock:
            if self._ambient_stop is stop_event:
                self._ambient_stop = None
            if self._ambient_thread and self._ambient_thread.ident == threading.get_ident():
                self._ambient_thread = None

    def _stop_ambient(self):
        with self._lock:
            stop_event = self._ambient_stop
            proc = self._ambient_proc
            self._ambient_stop = None
            self._ambient_thread = None
            self._ambient_proc = None
        if stop_event:
            stop_event.set()
        self._terminate_process(proc)
        self._forget_process(proc)

    def _stop_foreground(self):
        with self._lock:
            stop_event = self._foreground_stop
            proc = self._foreground_proc
            self._foreground_stop = None
            self._foreground_thread = None
            self._foreground_proc = None
            self._foreground_tag = ""
        if stop_event:
            stop_event.set()
        self._terminate_process(proc)
        self._forget_process(proc)

    def _play_foreground(
        self,
        path: Path,
        tag: str,
        loop: bool = False,
        volume_factor: float = 1.0,
        pause_ambient: bool = True,
    ):
        if not path.exists():
            return
        with self._lock:
            if not self._enabled:
                return
            if loop and self._foreground_tag == tag and self._foreground_thread and self._foreground_thread.is_alive():
                return
            base_volume = self._volume
        if pause_ambient:
            self._stop_ambient()
        self._stop_foreground()

        stop_event = threading.Event()
        worker = threading.Thread(
            target=self._foreground_worker,
            args=(
                path,
                tag,
                stop_event,
                loop,
                max(0.0, min(1.0, base_volume * volume_factor)),
                pause_ambient,
            ),
            daemon=True,
        )
        with self._lock:
            self._foreground_stop = stop_event
            self._foreground_thread = worker
            self._foreground_tag = tag
        worker.start()

    def _foreground_worker(
        self,
        path: Path,
        tag: str,
        stop_event: threading.Event,
        loop: bool,
        volume: float,
        resume_ambient: bool,
    ):
        while not stop_event.is_set():
            try:
                proc = self._start_afplay(path, volume)
            except Exception:
                break

            with self._lock:
                if self._foreground_stop is not stop_event or not self._enabled:
                    self._terminate_process(proc)
                    self._forget_process(proc)
                    break
                self._foreground_proc = proc

            while proc.poll() is None and not stop_event.wait(0.12):
                pass

            if stop_event.is_set():
                self._terminate_process(proc)

            with self._lock:
                if self._foreground_proc is proc:
                    self._foreground_proc = None
            if proc.poll() is not None:
                self._forget_process(proc)

            if not loop or stop_event.is_set():
                break
            time.sleep(0.08)

        with self._lock:
            if self._foreground_stop is stop_event:
                self._foreground_stop = None
                self._foreground_thread = None
                self._foreground_tag = ""
            should_restart = resume_ambient and self._enabled and self._foreground_stop is None
        if should_restart:
            self.start_ambient()

    def play_startup(self):
        self._play_foreground(_START_FILE, tag="start", loop=False, volume_factor=0.95)

    def play_power_up(self):
        self._play_foreground(_POWER_UP_FILE, tag="power_up", loop=False, volume_factor=0.95)

    def play_jarvis_lines(self):
        self._play_foreground(_JARVIS_LINES_FILE, tag="jarvis_lines", loop=False, volume_factor=0.95)

    def play_success(self):
        self._play_foreground(
            _DONE_FILE,
            tag="done",
            loop=False,
            volume_factor=0.68,
            pause_ambient=False,
        )

    def play_error(self):
        self._play_foreground(_ERROR_FILE, tag="error", loop=False, volume_factor=0.95)

    def start_thinking(self):
        self._play_foreground(
            _THINK_FILE,
            tag="think",
            loop=True,
            volume_factor=0.82,
            pause_ambient=False,
        )

    def stop_thinking(self):
        with self._lock:
            is_thinking = self._foreground_tag == "think"
        if is_thinking:
            self._stop_foreground()

    def toggle(self) -> bool:
        self.set_enabled(not self._enabled)
        return self._enabled

    def set_enabled(self, enabled: bool):
        enabled = bool(enabled)
        with self._lock:
            self._enabled = enabled
        if enabled:
            self.start_ambient()
        else:
            self._stop_ambient()
            self._stop_foreground()

    def set_volume(self, volume: float):
        with self._lock:
            self._volume = max(0.0, min(1.0, float(volume)))
            fg_tag = self._foreground_tag
            can_restart_ambient = self._enabled and not fg_tag
        if fg_tag == "think":
            self._stop_foreground()
            self.start_thinking()
        elif can_restart_ambient:
            self._stop_ambient()
            self.start_ambient()

    def stop_all(self):
        with self._lock:
            self._enabled = False
            ambient_stop = self._ambient_stop
            foreground_stop = self._foreground_stop
            procs = {
                proc
                for proc in (
                    self._ambient_proc,
                    self._foreground_proc,
                    *self._all_sound_procs,
                )
                if proc
            }
            self._ambient_stop = None
            self._ambient_thread = None
            self._ambient_proc = None
            self._foreground_stop = None
            self._foreground_thread = None
            self._foreground_proc = None
            self._foreground_tag = ""
            self._all_sound_procs.clear()
        if ambient_stop:
            ambient_stop.set()
        if foreground_stop:
            foreground_stop.set()
        for proc in procs:
            self._terminate_process(proc)

    def get_volume(self) -> float:
        return self._volume


# ─────────────────────────────────────────────────────────────────────────────

class JarvisUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("F.R.I.D.A.Y")
        self.root.update_idletasks()

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        margin_x = max(24, int(sw * 0.025))
        margin_y = max(54, int(sh * 0.055))
        self.W = min(max(640, sw - margin_x), sw, W_TARGET)
        self.H = min(max(520, sh - margin_y), sh, H_TARGET)
        _geo = f"{self.W}x{self.H}+{(sw-self.W)//2}+{max(0, (sh-self.H)//2 - 8)}"
        self.root.geometry(_geo)
        self.root.minsize(min(self.W, sw), min(self.H, sh))
        self.root.resizable(True, True)
        self.root.configure(bg=C_BG)
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        # macOS window manager bazen geometry'yi override eder, tekrar zorla.
        for delay in (80, 220, 600, 1200):
            self.root.after(delay, self._force_startup_size)
        # Birkaç saniye sonra topmost'u kapat (normal davranış)
        self.root.after(3000, lambda: self.root.attributes('-topmost', False))

        self._window_geometry = _geo
        self._normal_size = (self.W, self.H)
        self._fullscreen = True

        self._set_layout_metrics(self.W, self.H)

        # ── State ────────────────────────────────────────────────────────────
        self.speaking        = False
        self.user_speaking   = False
        self.muted           = False
        self.paused          = False
        self.scale           = 1.0
        self.target_scale    = 1.0
        self.halo_a          = 55.0
        self.target_halo     = 55.0
        self.last_t          = time.time()
        self.tick            = 0
        self.rings_spin      = [0.0, 45.0, 90.0, 200.0]  # 4 ayrı halka
        self.pulse_r         = []
        self.status_blink    = True
        self._jarvis_state   = "INITIALISING"
        self._user_speaking_until = 0.0

        # ── Health overlay ───────────────────────────────────────────────────
        self._health_visible  = False
        self._health_query    = "all"
        self._health_display  = ""
        self._health_hide_job = None
        self._weather_card = {
            "city": "Istanbul",
            "primary": "--",
            "details": ["Hava durumu yükleniyor..."],
        }
        self._health_card_lines = ["Sağlık özeti yükleniyor..."]
        self._panel_focus = ""
        self._panel_focus_until = 0.0
        self._brief_refresh_busy = False
        self._started_at = time.time()
        self._error_hold_until = 0.0
        self._settings_open = False
        self._settings_tab = "settings"
        self._debug_entries = deque(maxlen=160)
        self._startup_sfx_played = False
        self._theme_name = "dark"  # Aktif tema: "dark" veya "light"
        self._settings_geometry = {
            "btn_x": 14,
            "btn_y": 12,
            "btn_w": 250,
            "btn_h": 46,
            "panel_x": 14,
            "panel_y": HDR_H + 10,
            "panel_w": 320,
            "panel_h": 292,
        }
        self.setup_frame = None
        self.api_entry = None
        self.youtube_api_entry = None
        self.youtube_handle_entry = None

        # ── Empathy Core ─────────────────────────────────────────────────────
        self.user_emotion = "calm"
        self.emotion_expiry = 0.0

        # ── Callbacks ────────────────────────────────────────────────────────
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_stop_command = None
        self.on_voice_change = None
        self.on_effects_state_change = None
        self.on_rfid_bypass = None

        # ── Voice ────────────────────────────────────────────────────────────
        self._current_voice = self._load_voice()

        # ── Sound ────────────────────────────────────────────────────────────
        self.sound = SoundManager()

        # ── Stats ────────────────────────────────────────────────────────────
        self._stats      = {'cpu': 0.0, 'ram': 0.0, 'disk': 0.0,
                            'battery': 100.0, 'net_up': 0.0, 'net_down': 0.0}
        self._cpu_hist   = [0.0] * 24
        self._last_net   = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._wave_jarvis = [random.randint(4, 26) for _ in range(18)]
        self._wave_user   = [random.randint(2, 10) for _ in range(18)]

        # ── Typing ───────────────────────────────────────────────────────────
        self.typing_queue = deque()
        self.is_typing    = False

        # ── Partiküller (arka plan, az sayıda) ───────────────────────────────
        self.particles = [
            {
                'x':  random.uniform(0, self.W),
                'y':  random.uniform(0, self.H),
                'vx': random.uniform(-0.15, 0.15),
                'vy': random.uniform(-0.15, 0.15),
                'r':  random.uniform(0.5, 1.8),
                'a':  random.randint(15, 70),
            }
            for _ in range(24)
        ]

        self.orb_particles = [
            {
                'angle': random.uniform(0, math.tau),
                'orbit': random.uniform(0.06, 0.98),
                'speed': random.uniform(-0.030, 0.030),
                'size': random.uniform(0.8, 2.8),
                'phase': random.uniform(0, math.tau),
                'wobble': random.uniform(0.010, 0.040),
                'depth': random.uniform(0.30, 1.00),
            }
            for _ in range(160)
        ]
        self.orb_shell_particles = [
            {
                'angle': random.uniform(0, math.tau),
                'speed': random.uniform(-0.020, 0.020),
                'size': random.uniform(1.4, 3.8),
                'phase': random.uniform(0, math.tau),
                'glow': random.uniform(0.4, 1.0),
            }
            for _ in range(84)
        ]

        # ── Canvas ───────────────────────────────────────────────────────────
        self.bg = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=C_BG, highlightthickness=0)
        self.bg.place(x=0, y=0)

        # Panel states
        self._show_left_panel = True
        self._show_right_panel = True
        self.left_slide = 1.0
        self.right_slide = 1.0

        # ── Log ──────────────────────────────────────────────────────────────
        self.log_frame = tk.Frame(self.root, bg=C_PANEL,
                                  highlightbackground=C_MID,
                                  highlightthickness=1)
        self.log_frame.place(x=self.CHAT_X, y=self.CHAT_Y,
                             width=self.CHAT_W, height=self.CHAT_H)
        self.log_text = tk.Text(
            self.log_frame, fg=C_TEXT, bg=C_PANEL,
            insertbackground=C_TEXT, borderwidth=0,
            wrap="word", font=font_body(12), padx=12, pady=8)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        self.log_text.tag_config("you", foreground="#d0f0ee")
        self.log_text.tag_config("ai",  foreground=C_PRI)
        self.log_text.tag_config("sys", foreground=C_GOLD)
        self.log_text.tag_config("err", foreground=C_RED)

        self._build_input_bar(self.CHAT_W)
        self._build_mute_button()
        self._build_pause_button()
        self._build_shutdown_button()
        self._build_theme_button()
        self._build_ai_coder_button()
        self._build_panel_toggles()
        self._build_settings_panel()
        self._build_voice_selector(self._settings_body)
        self._build_sfx_button(self._settings_body)
        self._build_api_button(self._settings_body)
        self._build_fx_slider(self._settings_body)
        self._build_tools_panel()
        self._build_social_bar()
        self._layout_settings_controls()
        self._place_layout_widgets()

        # Orb tıklama = pause/resume
        self.bg.bind("<Button-1>", self._on_canvas_click)

        self.root.bind("<F4>",        lambda e: self._toggle_mute())
        self.root.bind("<Command-m>", lambda e: self._toggle_mute())
        self.root.bind("<Escape>",    lambda e: self._shutdown())
        self.root.bind("<F5>",        lambda e: self._toggle_pause())
        self.root.bind("<F11>",       lambda e: self._toggle_fullscreen())
        self.root.bind("<Command-f>", lambda e: self._toggle_fullscreen())
        self.root.bind("[",           lambda e: self._toggle_left_panel())
        self.root.bind("]",           lambda e: self._toggle_right_panel())

        self._api_key_ready = has_gemini_api_key()
        if not self._api_key_ready:
            self._show_setup_ui()

        self._effects_active = None
        self._sync_sound_state()
        self.root.after(180, self._play_startup_sfx_once)
        self._kick_brief_refresh()
        self.root.after(120, self._enter_fullscreen)
        self._animate()
        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)

    def _force_startup_size(self):
        if self._fullscreen:
            self._enter_fullscreen()
            return
        self.root.geometry(self._window_geometry)
        self._resize_surface(*self._normal_size)
        self.root.update_idletasks()

    def _enter_fullscreen(self):
        sw = max(self.root.winfo_screenwidth(), self.root.winfo_width(), self.W)
        sh = max(self.root.winfo_screenheight(), self.root.winfo_height(), self.H)
        self.root.attributes("-fullscreen", True)
        self.root.geometry(f"{sw}x{sh}+0+0")
        self._resize_surface(sw, sh)

    def _set_layout_metrics(self, width: int, height: int):
        self.W = int(width)
        self.H = int(height)
        self.LEFT_W = int(min(LEFT_W_T, int(self.W * 0.23)) * getattr(self, "left_slide", 1.0))
        self.RIGHT_W = int(min(RIGHT_W_T, int(self.W * 0.25)) * getattr(self, "right_slide", 1.0))
        center_w = self.W - self.LEFT_W - self.RIGHT_W
        orb_area_h = self.H - HDR_H - CONTROL_H - FOOTER_H - 24
        self.FCX = self.LEFT_W + center_w // 2
        self.FCY = HDR_H + orb_area_h // 2 + 6
        self.FACE = min(int(orb_area_h * 0.90), int(center_w * 0.86), 860)

        self.CENTER_X0 = self.LEFT_W
        self.CENTER_X1 = self.W - self.RIGHT_W
        self.CTRL_X = self.LEFT_W + 18
        self.CTRL_Y = HDR_H + orb_area_h + 2
        self.CTRL_W = center_w - 36
        self.CHAT_PANEL_X = self.W - self.RIGHT_W + 8
        self.CHAT_PANEL_Y = HDR_H + 8
        self.CHAT_PANEL_W = self.RIGHT_W - 14
        self.CHAT_PANEL_H = self.H - HDR_H - FOOTER_H - 16
        self.CHAT_X = self.CHAT_PANEL_X + 10
        self.CHAT_Y = self.CHAT_PANEL_Y + 34
        self.CHAT_W = self.CHAT_PANEL_W - 20
        self.CHAT_H = self.CHAT_PANEL_H - 90
        self.CHAT_INPUT_Y = self.CHAT_PANEL_Y + self.CHAT_PANEL_H - INPUT_H - 10

    # ── Social bar ───────────────────────────────────────────────────────────
    def _build_social_bar(self):
        ICON_SIZE = 18
        ICON_DIR  = BASE_DIR / "Icon"

        # Modern minimalist panel (Çerçeve ve kart Slate tasarımıyla tam uyumlu)
        bar = tk.Frame(self.root, bg=C_PANEL, highlightbackground=C_DIM, highlightthickness=1)
        self._social_bar = bar

        def _open(url):
            import webbrowser
            def open_url(e):
                try:
                    webbrowser.open(url)
                except Exception as e:
                    print(f"Tarayıcı açılamadı: {e}")
            return open_url

        def _load_icon(filename: str):
            try:
                img = Image.open(ICON_DIR / filename).convert("RGBA")
                img = img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                return None

        # Şık Segoe UI İsim etiketi
        name_lbl = tk.Label(
            bar, text="Samet Oymak",
            fg=C_TEXT, bg=C_PANEL,
            font=font_body_bold(9), cursor="hand2"
        )
        name_lbl.pack(side="left", padx=(12, 6))
        name_lbl.bind("<Button-1>", _open("https://www.instagram.com/sametoymakk_/"))
        name_lbl.bind("<Enter>", lambda e: name_lbl.configure(fg=C_PRI))
        name_lbl.bind("<Leave>", lambda e: name_lbl.configure(fg=C_TEXT))

        # Instagram & GitHub Logoları
        self._icon_ig = _load_icon("instagram-logo.png")
        self._icon_gh = _load_icon("github-logo.png")

        btn_style = {
            "bg": C_PANEL,
            "activebackground": C_DIM,
            "borderwidth": 0,
            "cursor": "hand2",
            "padx": 4
        }

        # Instagram
        if self._icon_ig:
            ig_lbl = tk.Label(bar, image=self._icon_ig, **btn_style)
            ig_lbl.pack(side="right", padx=(0, 12))
            ig_lbl.bind("<Button-1>", _open("https://www.instagram.com/sametoymakk_/"))
            ig_lbl.bind("<Enter>", lambda e: ig_lbl.configure(bg=C_DIM))
            ig_lbl.bind("<Leave>", lambda e: ig_lbl.configure(bg=C_PANEL))
        else:
            ig_lbl = tk.Label(bar, text="📸", fg=C_MUTED, font=font_body(10), **btn_style)
            ig_lbl.pack(side="right", padx=(0, 12))
            ig_lbl.bind("<Button-1>", _open("https://www.instagram.com/sametoymakk_/"))
            ig_lbl.bind("<Enter>", lambda e: ig_lbl.configure(fg=C_PRI, bg=C_DIM))
            ig_lbl.bind("<Leave>", lambda e: ig_lbl.configure(fg=C_MUTED, bg=C_PANEL))

        # GitHub
        if self._icon_gh:
            gh_lbl = tk.Label(bar, image=self._icon_gh, **btn_style)
            gh_lbl.pack(side="right", padx=(0, 4))
            gh_lbl.bind("<Button-1>", _open("https://github.com/Sametoymak99"))
            gh_lbl.bind("<Enter>", lambda e: gh_lbl.configure(bg=C_DIM))
            gh_lbl.bind("<Leave>", lambda e: gh_lbl.configure(bg=C_PANEL))
        else:
            gh_lbl = tk.Label(bar, text="🐙", fg=C_MUTED, font=font_body(10), **btn_style)
            gh_lbl.pack(side="right", padx=(0, 4))
            gh_lbl.bind("<Button-1>", _open("https://github.com/Sametoymak99"))
            gh_lbl.bind("<Enter>", lambda e: gh_lbl.configure(fg=C_PRI, bg=C_DIM))
            gh_lbl.bind("<Leave>", lambda e: gh_lbl.configure(fg=C_MUTED, bg=C_PANEL))

    # ── Tema butonu ───────────────────────────────────────────────────────────
    def _build_theme_button(self):
        BW, BH = 130, 32
        self._theme_canvas = tk.Canvas(
            self.root, width=BW, height=BH,
            bg=C_BG, highlightthickness=0, cursor="hand2")
        self._theme_canvas.bind("<Button-1>", lambda e: self._toggle_theme())
        self._draw_theme_button()

    def _draw_theme_button(self):
        if not hasattr(self, "_theme_canvas"):
            return
        c = self._theme_canvas
        BW = int(c["width"])
        BH = int(c["height"])
        c.delete("all")
        c.configure(bg=C_BG)
        if self._theme_name == "light":
            icon = "⚆ LIGHT"
            col = C_GOLD
        elif self._theme_name == "dark":
            icon = "☾ DARK"
            col = C_PRI
        else:
            icon = "⚡ NEXUS"
            col = C_ORG
        c.create_text(BW//2, BH//2, text=icon, fill=col, font=font_body_bold(10))

    def _toggle_theme(self):
        if self._theme_name == "light":
            self._theme_name = "dark"
        elif self._theme_name == "dark":
            self._theme_name = "nexus"
        else:
            self._theme_name = "light"
        _load_theme_globals(self._theme_name)
        self._apply_theme_widgets()
        self._draw_theme_button()
        save_app_config({"theme": self._theme_name})

    def _build_ai_coder_button(self):
        BW, BH = 140, 32
        self._ai_coder_canvas = tk.Canvas(
            self.root, width=BW, height=BH,
            bg=C_BG, highlightthickness=0, cursor="hand2")
        self._ai_coder_canvas.bind("<Button-1>", lambda e: self._run_coder_tool())
        self._draw_ai_coder_button()

    def _draw_ai_coder_button(self):
        if not hasattr(self, "_ai_coder_canvas"):
            return
        c = self._ai_coder_canvas
        BW = int(c["width"])
        BH = int(c["height"])
        c.delete("all")
        c.configure(bg=C_BG)
        c.create_text(BW//2, BH//2, text="💻  AI CODER", fill=C_PRI, font=font_body_bold(10))

    def _apply_theme_widgets(self):
        """Tüm statik widget'ların renklerini aktif temaya göre günceller."""
        try:
            # Kök pencere ve canvas arkaplanı
            self.root.configure(bg=C_BG)
            self.bg.configure(bg=C_BG)

            # Log paneli
            self.log_frame.configure(bg=C_PANEL, highlightbackground=C_MID)
            self.log_text.configure(fg=C_TEXT, bg=C_PANEL)
            self.log_text.tag_config("you", foreground=C_TEXT)
            self.log_text.tag_config("ai",  foreground=C_PRI)
            self.log_text.tag_config("sys", foreground=C_GOLD)
            self.log_text.tag_config("err", foreground=C_RED)

            # Input ve send button
            self._input_entry.configure(
                fg=C_TEXT, bg=C_PANEL,
                highlightbackground=C_DIM, highlightcolor=C_PRI)
            self._send_btn.configure(
                fg=C_ORG, bg=C_PANEL,
                activeforeground=C_BG, activebackground=C_ORG,
                highlightbackground=C_ORG)

            # Kontrol butonları (canvas) arkaplanları
            for cv in (self._mute_canvas, self._pause_canvas,
                       self._shutdown_canvas, self._settings_btn_canvas,
                       self._theme_canvas, getattr(self, "_ai_coder_canvas", None)):
                if cv and hasattr(cv, "configure"):
                    cv.configure(bg=C_BG)

            # Settings panel
            if self._theme_name == "nexus":
                panel_bg = "#080c1b"
            elif self._theme_name == "dark":
                panel_bg = "#041111"
            else:
                panel_bg = "#e8f4f2"
                
            self._settings_panel.configure(bg=panel_bg, highlightbackground=C_MID)
            self._settings_title.configure(fg=C_PRI, bg=panel_bg)
            self._settings_body.configure(bg=panel_bg)
            self._debug_body.configure(bg=panel_bg)
            self._settings_sfx_label.configure(fg=C_MID, bg=panel_bg)
            self._settings_status_primary.configure(fg=C_TEXT, bg=panel_bg)
            self._settings_status_secondary.configure(fg=C_MID, bg=panel_bg)
            self._volume_label.configure(fg=C_PRI, bg=panel_bg)
            self._volume_scale.configure(bg=panel_bg, fg=C_TEXT, activebackground=C_PRI)
            self._voice_label.configure(fg=C_MID, bg=panel_bg)
            self._voice_menu.configure(fg=C_PRI, bg=C_PANEL, activeforeground=C_BG,
                                       activebackground=C_PRI, highlightbackground=C_MID)
            self._voice_menu["menu"].configure(fg=C_PRI, bg=C_PANEL,
                                               activeforeground=C_BG, activebackground=C_PRI)

            # Debug text
            if self._theme_name == "nexus":
                debug_bg = "#040814"
            elif self._theme_name == "dark":
                debug_bg = "#020a0a"
            else:
                debug_bg = "#e0f0f0"
                
            self._debug_text.configure(fg=C_TEXT, bg=debug_bg, highlightbackground=C_DIM)
            self._debug_text.tag_config("info", foreground=C_TEXT)
            self._debug_text.tag_config("warn", foreground=C_GOLD)
            self._debug_text.tag_config("err",  foreground=C_RED)

            # Sosyal bar
            if hasattr(self, "_social_bar"):
                self._social_bar.configure(bg=C_BG)
                for child in self._social_bar.winfo_children():
                    try:
                        child.configure(bg=C_BG)
                    except Exception:
                        pass

            # STATE_HEX_COLORS güncelle
            import ui as _ui_mod
            _ui_mod.STATE_HEX_COLORS.update({
                "LISTENING": C_GREEN,
                "SPEAKING":  C_BLUE,
                "THINKING":  C_GOLD,
                "INITIALISING": C_RED,
                "ERROR":     C_RED,
            })

            # Düğmeleri yeniden çiz
            self._draw_mute_button()
            self._draw_pause_button()
            self._draw_shutdown_button()
            self._draw_theme_button()
            self._draw_panel_toggles()
            if hasattr(self, "_draw_ai_coder_button"):
                self._draw_ai_coder_button()

        except Exception as ex:
            print(f"[THEME] Widget güncelleme hatası: {ex}")

    # ── Voice ─────────────────────────────────────────────────────────────────

    def _load_voice(self) -> str:
        try:
            return str(load_app_config().get("voice", "Charon") or "Charon")
        except Exception:
            return "Charon"

    # ── Shutdown button (sağ alt, büyük) ────────────────────────────────────
    def _build_shutdown_button(self):
        BW, BH = 140, 36
        self._shutdown_canvas = tk.Canvas(
            self.root, width=BW, height=BH,
            bg=C_BG, highlightthickness=0, cursor="hand2")
        self._shutdown_canvas.bind("<Button-1>", lambda e: self._shutdown())
        self._draw_shutdown_button()

    def _draw_shutdown_button(self):
        c = self._shutdown_canvas
        BW, BH = 140, 36
        c.delete("all")
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        c.create_text(BW//2, BH//2, text="⏻  Sistemi Kapat",
                      fill=C_RED, font=font_body_bold(10))

    def _build_settings_panel(self):
        geo = self._settings_geometry
        self._settings_btn_canvas = tk.Canvas(
            self.root,
            width=geo["btn_w"],
            height=geo["btn_h"],
            bg=C_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self._settings_btn_canvas.place(x=geo["btn_x"], y=geo["btn_y"])
        self._settings_btn_canvas.bind("<Button-1>", lambda e: self._toggle_settings_panel())
        self._draw_settings_button()

        self._settings_panel = tk.Frame(
            self.root,
            bg=C_PANEL,
            highlightbackground=C_MID,
            highlightthickness=1,
        )
        self._settings_panel.place_forget()
        self._settings_title = tk.Label(
            self._settings_panel,
            text="SETTINGS",
            fg=C_PRI,
            bg=C_PANEL,
            font=font_display(11),
        )
        self._settings_tab_settings = tk.Canvas(
            self._settings_panel,
            width=108,
            height=28,
            bg=C_PANEL,
            highlightthickness=0,
            cursor="hand2",
        )
        self._settings_tab_settings.bind("<Button-1>", lambda e: self._set_settings_tab("settings"))
        
        self._settings_tab_debug = tk.Canvas(
            self._settings_panel,
            width=96,
            height=28,
            bg=C_PANEL,
            highlightthickness=0,
            cursor="hand2",
        )
        self._settings_tab_debug.bind("<Button-1>", lambda e: self._set_settings_tab("debug"))
        
        self._settings_body = tk.Frame(self._settings_panel, bg=C_PANEL)
        self._debug_body = tk.Frame(self._settings_panel, bg=C_PANEL)
        self._settings_sfx_label = tk.Label(
            self._settings_body,
            text="SFX",
            fg=C_MID,
            bg=C_PANEL,
            font=font_body_bold(8),
        )
        self._settings_status_primary = tk.Label(
            self._settings_body,
            text="",
            fg=C_TEXT,
            bg=C_PANEL,
            font=font_body_bold(9),
            anchor="w",
            justify="left",
        )
        self._settings_status_secondary = tk.Label(
            self._settings_body,
            text="",
            fg=C_MID,
            bg=C_PANEL,
            font=font_body(9),
            anchor="w",
            justify="left",
        )
        self._debug_text = tk.Text(
            self._debug_body,
            fg=C_TEXT,
            bg=C_BG,
            insertbackground=C_TEXT,
            borderwidth=0,
            wrap="word",
            font=font_body(10),
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground=C_DIM,
        )
        self._debug_text.tag_config("info", foreground=C_TEXT)
        self._debug_text.tag_config("warn", foreground=C_GOLD)
        self._debug_text.tag_config("err", foreground=C_RED)
        self._debug_text.configure(state="disabled")
        self._draw_settings_tabs()
        self._render_debug_logs()
        self._refresh_settings_status()

    def _draw_settings_button(self):
        c = self._settings_btn_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        accent = C_BLUE if self._settings_open else C_MID
        inner = C_DIM if self._settings_open else C_BG
        c.create_rectangle(0, 0, bw, bh, fill=inner, outline="")
        
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        
        c.create_text(14, 15, text="SYSTEM SETTINGS", fill=C_PRI, font=font_display(10), anchor="w")
        c.create_text(14, 33, text=MODEL_BADGE, fill=C_MUTED, font=font_body(9), anchor="w")
        c.create_text(bw - 14, bh // 2, text="▾" if self._settings_open else "▸",
                      fill=accent, font=font_display(14), anchor="e")

    def _toggle_settings_panel(self):
        self._settings_open = not self._settings_open
        self._draw_settings_button()
        self._place_layout_widgets()

    def _draw_settings_tabs(self):
        for key, canvas, label in (
            ("settings", self._settings_tab_settings, "SETTINGS"),
            ("debug",    self._settings_tab_debug, "DEBUG")
        ):
            active = (self._settings_tab == key)
            fg = C_PRI if active else C_MUTED
            bg = C_DIM if active else C_PANEL
            canvas.delete("all")
            canvas.configure(bg=bg)
            w = int(canvas["width"])
            h = int(canvas["height"])
            canvas.create_text(w//2, h//2, text=label, fill=fg, font=font_display(9))

    def _run_coder_tool(self):
        # Premium, Slate/Concentric temalı çerçevesiz (borderless) otonom coder modalı
        dialog = tk.Toplevel(self.root)
        dialog.configure(bg=C_BG)
        dialog.resizable(False, False)
        
        # Ekranın tam ortasına konumlandırma
        dialog_w, dialog_h = 500, 360
        rx = self.root.winfo_rootx() + (self.W - dialog_w) // 2
        ry = self.root.winfo_rooty() + (self.H - dialog_h) // 2
        dialog.geometry(f"{dialog_w}x{dialog_h}+{rx}+{ry}")
        
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Ultra premium çift katmanlı teknolojik neon çeper etkisi
        dialog.configure(highlightthickness=2, highlightbackground=C_PRI)
        dialog.overrideredirect(True)
        dialog.attributes("-topmost", True)
        dialog.lift()
        
        # Ana içerik çerçevesi (Breathing room & Padding)
        content = tk.Frame(dialog, bg=C_BG, padx=24, pady=22)
        content.pack(fill="both", expand=True)
        
        # --- ÜST BAŞLIK & AKILLI CANVAS DEKORASYONU ---
        header_frame = tk.Frame(content, bg=C_BG)
        header_frame.pack(fill="x", pady=(0, 6))
        
        title_lbl = tk.Label(header_frame, text="💻  F.R.I.D.A.Y. OTONOM CODER", 
                             fg=C_PRI, bg=C_BG, font=font_display(12))
        title_lbl.pack(side="left")
        
        # Küçük süsleyici neon çizgi ve Kapat Butonu
        decor_canvas = tk.Canvas(header_frame, width=100, height=2, bg=C_BG, highlightthickness=0)
        decor_canvas.pack(side="right", padx=(10, 0), pady=10)
        decor_canvas.create_line(0, 1, 100, 1, fill=C_ORG2, width=2)

        close_btn = tk.Label(header_frame, text="✕", fg=C_MUTED, bg=C_BG, font=font_body_bold(12), cursor="hand2")
        close_btn.pack(side="right", padx=10)
        close_btn.bind("<Button-1>", lambda e: dialog.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.configure(fg=C_RED))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(fg=C_MUTED))
        
        desc_text = ("Sadece hedefinizi belirtin. F.R.I.D.A.Y. otonom olarak kodları yazar, "
                     "sanal ortam kurup test eder ve tüm hataları kendi kendine giderir.")
        desc_lbl = tk.Label(content, text=desc_text, fg=C_MUTED, bg=C_BG, 
                            font=font_body(9), justify="left", wraplength=450, anchor="w")
        desc_lbl.pack(fill="x", pady=(0, 12))
        
        # --- MOTOR DURUM BİLGİSİ (Kapsül Tasarım) ---
        from autonomous_coder import is_ollama_running, get_installed_ollama_models
        ollama_ok = is_ollama_running()
        models = get_installed_ollama_models() if ollama_ok else []
        best_model = None
        for m in models:
            if any(x in m.lower() for x in ["coder", "qwen", "deepseek", "llama", "gemma"]):
                best_model = m
                break
        if models and not best_model:
            best_model = models[0]
            
        if ollama_ok and best_model:
            status_txt = f" ●   Motor: Gemini + Yerel Ollama [Hazır: {best_model}]"
            status_fg = C_GREEN
        elif ollama_ok:
            status_txt = " ●   Motor: Gemini [Yerel Ollama: Model Eksik (qwen2.5-coder önerilir)]"
            status_fg = C_GOLD
        else:
            status_txt = " ●   Motor: Gemini Bulut Çekirdeği [Yerel Ollama: Çevrimdışı]"
            status_fg = C_BLUE
            
        status_frame = tk.Frame(content, bg=C_DIMMER, highlightthickness=1, highlightbackground=C_MID, padx=12, pady=6)
        status_frame.pack(fill="x", pady=(0, 16))
        
        status_lbl = tk.Label(status_frame, text=status_txt, fg=status_fg, bg=C_DIMMER, 
                              font=font_body_bold(8), anchor="w")
        status_lbl.pack(fill="x")
        
        # --- FORM ELEMANLARI ---
        
        # 1. Proje Dosya Adı Girişi
        file_frame = tk.Frame(content, bg=C_BG)
        file_frame.pack(fill="x", pady=(0, 12))
        
        file_label = tk.Label(file_frame, text="Proje Dosyası Adı:", fg=C_MUTED, bg=C_BG, font=font_body_bold(9))
        file_label.pack(anchor="w", pady=(0, 4))
        
        filename_var = tk.StringVar(value="generated_project.py")
        file_entry = tk.Entry(file_frame, textvariable=filename_var, fg=C_TEXT, bg=C_PANEL,
                              insertbackground=C_TEXT, borderwidth=0, font=font_body(10),
                              highlightthickness=1, highlightbackground=C_MID, highlightcolor=C_ORG2)
        file_entry.pack(fill="x", ipady=6)
        
        # 2. Görev Girişi
        task_frame = tk.Frame(content, bg=C_BG)
        task_frame.pack(fill="x", pady=(0, 20))
        
        task_label = tk.Label(task_frame, text="Yapılmasını İstediğiniz Kodlama Görevi:", fg=C_MUTED, bg=C_BG, font=font_body_bold(9))
        task_label.pack(anchor="w", pady=(0, 4))
        
        task_var = tk.StringVar()
        entry = tk.Entry(task_frame, textvariable=task_var, fg=C_TEXT, bg=C_PANEL,
                         insertbackground=C_TEXT, borderwidth=0, font=font_body(11),
                         highlightthickness=1, highlightbackground=C_MID, highlightcolor=C_PRI)
        entry.pack(fill="x", ipady=8)
        entry.focus_set()
        
        # Focus-in / Focus-out Neon Parlama Efektleri
        def on_focus_in(e, color):
            e.widget.configure(highlightbackground=color, highlightthickness=1)
            
        def on_focus_out(e, color):
            e.widget.configure(highlightbackground=C_MID, highlightthickness=1)
            
        file_entry.bind("<FocusIn>", lambda e: on_focus_in(e, C_ORG2))
        file_entry.bind("<FocusOut>", lambda e: on_focus_out(e, C_MID))
        entry.bind("<FocusIn>", lambda e: on_focus_in(e, C_PRI))
        entry.bind("<FocusOut>", lambda e: on_focus_out(e, C_MID))
        
        # --- BUTONLAR ---
        btn_frame = tk.Frame(content, bg=C_BG)
        btn_frame.pack(fill="x")
        
        def _cancel():
            dialog.destroy()
            
        def _start():
            task = task_var.get().strip()
            filepath = filename_var.get().strip()
            if not task:
                return
            dialog.destroy()
            
            def _work():
                self.write_log(f"SYS: '{task}' görevi için ({filepath}) otonom kodlama başlatıldı. Lütfen bekleyin...")
                try:
                    from autonomous_coder import generate_and_run_code
                    res = generate_and_run_code(task, filepath=filepath)
                    self.write_log(res)
                    self.play_success_sfx()
                except Exception as e:
                    self.write_log(f"ERR: Kod üretimi başarısız: {e}")
                    self.play_error_sfx()
            threading.Thread(target=_work, daemon=True).start()
            
        entry.bind("<Return>", lambda e: _start())
        entry.bind("<Escape>", lambda e: _cancel())
        
        # Flat Premium Butonlar (Interactive Hover Animations)
        cancel_btn = tk.Button(btn_frame, text="İPTAL ET", command=_cancel, fg=C_TEXT, bg=C_DIM,
                               activeforeground=C_TEXT, activebackground=C_RED,
                               font=font_body_bold(9), borderwidth=0, cursor="hand2", padx=20, pady=8)
        cancel_btn.pack(side="right", padx=(12, 0))
        
        start_btn = tk.Button(btn_frame, text="OTONOM PROJEYİ BAŞLAT", command=_start, fg=C_BG, bg=C_PRI,
                              activeforeground=C_TEXT, activebackground=C_ORG,
                              font=font_body_bold(9), borderwidth=0, cursor="hand2", padx=24, pady=8)
        start_btn.pack(side="right")
        
        # Hover olay bağlayıcıları
        def on_btn_enter(btn, hover_bg, hover_fg):
            btn.configure(bg=hover_bg, fg=hover_fg)
            
        def on_btn_leave(btn, idle_bg, idle_fg):
            btn.configure(bg=idle_bg, fg=idle_fg)
            
        cancel_btn.bind("<Enter>", lambda e: on_btn_enter(cancel_btn, C_RED, C_TEXT))
        cancel_btn.bind("<Leave>", lambda e: on_btn_leave(cancel_btn, C_DIM, C_TEXT))
        
        start_btn.bind("<Enter>", lambda e: on_btn_enter(start_btn, C_ORG, C_TEXT))
        start_btn.bind("<Leave>", lambda e: on_btn_leave(start_btn, C_PRI, C_BG))(file_frame, textvariable=filename_var, fg="#ffffff", bg="#1e293b",
                              insertbackground="#ffffff", borderwidth=0, font=font_body(10),
                              highlightthickness=1, highlightbackground="#334155", highlightcolor=C_PRI, width=22)
        file_entry.pack(side="left", padx=10, ipady=4)

        # Metin giriş alanı (Görev)
        task_var = tk.StringVar()
        entry = tk.Entry(content, textvariable=task_var, fg="#ffffff", bg="#1e293b",
                         insertbackground="#ffffff", borderwidth=0, font=font_body(11),
                         highlightthickness=1, highlightbackground="#334155", highlightcolor=C_PRI)
        entry.pack(fill="x", ipady=8, pady=(0, 18))
        entry.focus_set()
        
        # Butonlar
        btn_frame = tk.Frame(content, bg=C_BG)
        btn_frame.pack(fill="x")
        
        def _cancel():
            dialog.destroy()
            
        def _start():
            task = task_var.get().strip()
            filepath = filename_var.get().strip()
            if not task:
                return
            dialog.destroy()
            
            def _work():
                self.write_log(f"SYS: '{task}' görevi için ({filepath}) otonom kodlama başlatıldı. Lütfen bekleyin...")
                try:
                    from autonomous_coder import generate_and_run_code
                    res = generate_and_run_code(task, filepath=filepath)
                    self.write_log(res)
                    self.play_success_sfx()
                except Exception as e:
                    self.write_log(f"ERR: Kod üretimi başarısız: {e}")
                    self.play_error_sfx()
            threading.Thread(target=_work, daemon=True).start()
            
        entry.bind("<Return>", lambda e: _start())
        entry.bind("<Escape>", lambda e: _cancel())
        
        cancel_btn = tk.Button(btn_frame, text="İPTAL", command=_cancel, fg=C_TEXT, bg=C_PANEL,
                               activeforeground=C_BG, activebackground=C_MUTED,
                               font=font_body_bold(9), borderwidth=0, cursor="hand2", padx=16, pady=6)
        cancel_btn.pack(side="right", padx=(10, 0))
        
        start_btn = tk.Button(btn_frame, text="PROJEYİ BAŞLAT", command=_start, fg=C_BG, bg=C_PRI,
                              activeforeground=C_BG, activebackground=C_PRI,
                              font=font_body_bold(9), borderwidth=0, cursor="hand2", padx=16, pady=6)
        start_btn.pack(side="right")

    def _build_tools_panel(self):
        self._tools_panel = tk.Frame(
            self.root,
            bg=C_PANEL,
            highlightthickness=0,
        )
        
        # Premium Slate Theme Button Factory with Hover Effects
        def create_tool_btn(text, command, highlight_color=C_PRI):
            btn = tk.Button(self._tools_panel, text=text, command=command,
                            fg=C_TEXT, bg=C_DIM, activeforeground=C_TEXT, activebackground=highlight_color,
                            font=font_body_bold(9), borderwidth=0, cursor="hand2", padx=12, pady=6, relief="flat")
            btn.pack(fill="x", pady=4)
            
            def on_enter(e):
                btn.configure(bg=highlight_color, fg=C_BG)
            def on_leave(e):
                btn.configure(bg=C_DIM, fg=C_TEXT)
                
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
            return btn
            
        create_tool_btn("☀️  Duvar Kağıdını Eşitle", lambda: self._run_wallpaper_tool() if hasattr(self, '_run_wallpaper_tool') else None, C_BLUE)
        create_tool_btn("📝  Günlük Brifingi Başlat", lambda: self._run_briefing_tool() if hasattr(self, '_run_briefing_tool') else None, C_ORG)
        create_tool_btn("📸  Ekran Görüntüsü Paylaş", lambda: self._run_screenshot_tool() if hasattr(self, '_run_screenshot_tool') else None, C_GREEN)
        
        # Otonom Coder for tools panel
        create_tool_btn("💻  Otonom Geliştiriciyi Başlat (Coder)", self._run_coder_tool, C_PRI)

    def _run_wallpaper_tool(self):
        # To be overridden by main.py or other controllers
        pass

    def _run_briefing_tool(self):
        pass

    def _run_screenshot_tool(self):
        pass

    def _layout_settings_controls(self):
        inner_w = self._settings_geometry["panel_w"] - 24
        self._api_canvas.place(x=0, y=2)
        self._sfx_canvas.place(x=inner_w - int(self._sfx_canvas["width"]) - 4, y=0)
        self._settings_status_primary.place(x=0, y=38, width=inner_w)
        self._settings_status_secondary.place(x=0, y=58, width=inner_w)
        self._settings_sfx_label.place(x=0, y=92)
        self._volume_label.place(x=0, y=116)
        self._volume_scale.place(x=0, y=136, width=inner_w, height=26)
        self._voice_label.place(x=0, y=178)
        self._voice_menu.place(x=88, y=172, width=inner_w - 88, height=30)

    def _refresh_settings_status(self):
        if not hasattr(self, "_settings_status_primary"):
            return
        cfg = load_app_config()
        gemini_ready = bool(str(cfg.get("gemini_api_key", "") or "").strip())
        yt_key_ready = bool(str(cfg.get("youtube_api_key", "") or "").strip())
        yt_handle = str(cfg.get("youtube_channel_handle", "") or "").strip()

        primary = [
            "Gemini Hazır" if gemini_ready else "Gemini API Eksik",
            "YouTube Hazır" if yt_key_ready and yt_handle else "YouTube Ayarı Eksik",
        ]
        if yt_handle:
            handle_text = yt_handle
        else:
            handle_text = "@handle girilmedi"
        secondary = f"Kanal: {handle_text}"

        self._settings_status_primary.configure(text="  ·  ".join(primary))
        self._settings_status_secondary.configure(text=secondary)

    def write_debug(self, text: str, level: str = "INFO"):
        clean = " ".join(str(text or "").split())
        if not clean:
            return
        self.root.after(0, self._append_debug_entry, clean, level)

    def _append_debug_entry(self, text: str, level: str = "INFO"):
        stamp = time.strftime("%H:%M:%S")
        lvl = (level or "INFO").upper()
        self._debug_entries.append((lvl, f"[{stamp}] {lvl}: {text}"))
        self._render_debug_logs()

    def _render_debug_logs(self):
        if not hasattr(self, "_debug_text"):
            return
        self._debug_text.configure(state="normal")
        self._debug_text.delete("1.0", tk.END)
        if not self._debug_entries:
            self._debug_text.insert(tk.END, "Henüz not edilebilir hata yok.\n", "info")
        else:
            for level, line in self._debug_entries:
                tag = "err" if level == "ERROR" else "warn" if level == "WARN" else "info"
                self._debug_text.insert(tk.END, line + "\n", tag)
        self._debug_text.see(tk.END)
        self._debug_text.configure(state="disabled")

    def _build_api_button(self, parent=None):
        parent = parent or self.root
        bw, bh = 154, 28
        self._api_canvas = tk.Canvas(
            parent, width=bw, height=bh,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._api_canvas.bind("<Button-1>", lambda e: self._open_api_settings())
        self._draw_api_button()

    def _draw_api_button(self):
        c = self._api_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        c.create_text(bw // 2, bh // 2, text="⌘ API Ayarları",
                      fill=C_BLUE, font=font_body_bold(10))

    def _build_fx_slider(self, parent=None):
        parent = parent or self.root
        slider_w = 280
        self._volume_label = tk.Label(
            parent,
            text=f"Ses Efektleri  {int(self.sound.get_volume() * 100)}%",
            fg=C_PRI,
            bg=parent.cget("bg"),
            font=font_body_bold(10),
        )
        self._volume_scale = tk.Scale(
            parent,
            from_=0,
            to=100,
            orient="horizontal",
            length=slider_w,
            showvalue=False,
            resolution=1,
            troughcolor="#071818",
            bg=parent.cget("bg"),
            fg=C_TEXT,
            activebackground=C_PRI,
            highlightthickness=0,
            borderwidth=0,
            sliderlength=18,
            width=10,
            command=self._on_volume_change,
        )
        self._volume_scale.set(int(self.sound.get_volume() * 100))

    def _on_volume_change(self, value):
        try:
            volume = max(0, min(100, int(float(value))))
        except (TypeError, ValueError):
            return
        self._volume_label.configure(text=f"Ses Efektleri  {volume}%")
        self.sound.set_volume(volume / 100.0)

    def _play_startup_sfx_once(self):
        pass

    def _sync_sound_state(self):
        enabled = self._sfx_on and not self.paused
        self.sound.set_enabled(enabled)
        if enabled and self._jarvis_state == "THINKING":
            self.sound.start_thinking()
        if enabled != self._effects_active:
            self._effects_active = enabled
            if self.on_effects_state_change:
                threading.Thread(
                    target=self.on_effects_state_change,
                    args=(enabled,),
                    daemon=True,
                ).start()

    def _open_api_settings(self):
        self._show_setup_ui(edit_mode=self._api_key_ready)

    def _close_setup_ui(self):
        if self.setup_frame and self.setup_frame.winfo_exists():
            self.setup_frame.destroy()
        self.setup_frame = None
        self.api_entry = None
        self.youtube_api_entry = None
        self.youtube_handle_entry = None

    # ── SFX toggle ───────────────────────────────────────────────────────────
    def _build_sfx_button(self, parent=None):
        parent = parent or self.root
        BW, BH = 98, 36
        self._sfx_canvas = tk.Canvas(parent, width=BW, height=BH,
                                     bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._sfx_canvas.bind("<Button-1>", lambda e: self._toggle_sfx())
        self._sfx_on = True
        self._draw_sfx_button()

    def _draw_sfx_button(self):
        c = self._sfx_canvas
        BW = int(c["width"])
        BH = int(c["height"])
        c.delete("all")
        col  = C_PRI if self._sfx_on else C_MID
        text = "♪ SFX: Açık"  if self._sfx_on else "♪ SFX: Kapalı"
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        c.create_text(BW//2, BH//2, text=text, fill=col, font=font_body_bold(9))

    def _toggle_sfx(self):
        self._sfx_on = not self._sfx_on
        self._draw_sfx_button()
        self._sync_sound_state()

    def _build_voice_selector(self, parent=None):
        parent = parent or self.root
        self._voice_var = tk.StringVar(value=self._current_voice)
        self._voice_label = tk.Label(parent, text="Asistan Sesi:", fg=C_MID, bg=parent.cget("bg"),
                                     font=font_body_bold(9))

        self._voice_menu = tk.OptionMenu(parent, self._voice_var, *VOICES,
                                         command=self._on_voice_select)
        self._voice_menu.config(
            fg=C_PRI, bg=C_PANEL, activeforeground=C_BG,
            activebackground=C_PRI, font=font_body(10),
            borderwidth=0, highlightthickness=1,
            highlightbackground=C_MID, width=12)
        self._voice_menu["menu"].config(
            fg=C_PRI, bg=C_PANEL, font=font_body(10),
            activeforeground=C_BG, activebackground=C_PRI)

    def _on_voice_select(self, voice: str):
        self._current_voice = voice
        save_app_config({"voice": voice})
        if self.on_voice_change:
            threading.Thread(target=self.on_voice_change, args=(voice,), daemon=True).start()

    # ── Mute button ──────────────────────────────────────────────────────────
    def _build_mute_button(self):
        self._mute_canvas = tk.Canvas(self.root, width=126, height=36,
                                      bg=C_BG, highlightthickness=0, cursor="hand2")
        self._mute_canvas.bind("<Button-1>", lambda e: self._toggle_mute())
        self._draw_mute_button()

    def _draw_mute_button(self):
        c = self._mute_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        if self.muted:
            col, icon, lbl = C_MUTED, "🔇", " MUTED"
        else:
            col, icon, lbl = C_GREEN, "🎙", " LIVE"
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        c.create_text(bw//2, bh//2, text=f"{icon}{lbl}",
                      fill=col, font=font_body_bold(11))

    def _build_pause_button(self):
        self._pause_canvas = tk.Canvas(self.root, width=126, height=36,
                                       bg=C_BG, highlightthickness=0, cursor="hand2")
        self._pause_canvas.bind("<Button-1>", lambda e: self._toggle_pause())
        self._draw_pause_button()

    def _draw_pause_button(self):
        c = self._pause_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        if self.paused:
            col, text = C_GOLD, "▶ RESUME"
        else:
            col, text = C_BLUE, "⏸ PAUSE"
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(11))

    def _toggle_mute(self):
        self.muted = not self.muted
        self._draw_mute_button()
        if self.muted:
            self.write_log("SYS: Mikrofon kapatıldı.")
        else:
            self.write_log("SYS: Mikrofon açık.")
        self._sync_sound_state()

    # ── Orb tıklama = pause ──────────────────────────────────────────────────
    def _on_canvas_click(self, event):
        dx = event.x - self.FCX
        dy = event.y - self.FCY
        if dx*dx + dy*dy <= (self.FACE * 0.40)**2:
            self._toggle_pause()

    def _toggle_pause(self):
        self.paused = not self.paused
        self._draw_pause_button()
        if self.paused:
            self.set_state("PAUSED")
            self.write_log("SYS: F.R.I.D.A.Y duraklatıldı.")
        else:
            self.set_state("THINKING")
            self.write_log("SYS: F.R.I.D.A.Y devam ediyor...")
        self._sync_sound_state()
        if self.on_pause_toggle:
            threading.Thread(target=self.on_pause_toggle, args=(self.paused,), daemon=True).start()

    def _shutdown(self):
        self.sound.stop_all()
        self.write_log("SYS: F.R.I.D.A.Y kapatılıyor...")
        lock_file = Path(__file__).resolve().parent / "friday.lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
            except Exception:
                pass
        self.root.after(380, os._exit, 0)

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self._enter_fullscreen()
        else:
            self.root.attributes("-fullscreen", False)
            self.root.geometry(self._window_geometry)
            self._resize_surface(*self._normal_size)

    def _resize_surface(self, width: int, height: int):
        self._set_layout_metrics(width, height)
        self.bg.configure(width=self.W, height=self.H)
        self.bg.place(x=0, y=0)
        self._place_layout_widgets()
        if hasattr(self, "_social_bar"):
            self._social_bar.place(x=14, y=self.H - FOOTER_H - 52)
        for p in self.particles:
            p["x"] %= self.W
            p["y"] %= self.H

    # ── Input bar ────────────────────────────────────────────────────────────
    def _build_input_bar(self, lw: int):
        x0 = self.CHAT_X
        btn_w = 76
        gap = 8
        inp_w = lw - btn_w - gap

        self._input_var   = tk.StringVar()
        self._input_entry = tk.Entry(
            self.root, textvariable=self._input_var,
            fg=C_TEXT, bg=C_BG, insertbackground=C_TEXT,
            borderwidth=0, font=font_body(11),
            highlightthickness=1, highlightbackground=C_DIM,
            highlightcolor=C_PRI)
        self._input_entry.place(
            x=x0, y=self.CHAT_INPUT_Y, width=inp_w, height=INPUT_H)
        self._input_entry.bind("<Return>",   self._on_input_submit)
        self._input_entry.bind("<KP_Enter>", self._on_input_submit)

        self._send_btn = tk.Button(
            self.root, text="SEND ▸",
            command=self._on_input_submit,
            fg=C_ORG, bg=C_PANEL,
            activeforeground=C_BG, activebackground=C_ORG,
            font=font_body_bold(10),
            borderwidth=0, cursor="hand2",
            highlightthickness=1, highlightbackground=C_ORG)

    def _toggle_left_panel(self):
        self._show_left_panel = not self._show_left_panel
        self._place_layout_widgets()
        self._draw_panel_toggles()

    def _toggle_right_panel(self):
        self._show_right_panel = not self._show_right_panel
        self._place_layout_widgets()
        self._draw_panel_toggles()

    def _build_panel_toggles(self):
        self._left_toggle = tk.Canvas(self.root, width=24, height=60, bg=C_PANEL, highlightthickness=1, highlightbackground=C_DIM, cursor="hand2")
        self._left_toggle.bind("<Button-1>", lambda e: self._toggle_left_panel())
        
        self._right_toggle = tk.Canvas(self.root, width=24, height=60, bg=C_PANEL, highlightthickness=1, highlightbackground=C_DIM, cursor="hand2")
        self._right_toggle.bind("<Button-1>", lambda e: self._toggle_right_panel())
        
        self._draw_panel_toggles()

    def _draw_panel_toggles(self):
        lc = self._left_toggle
        lc.delete("all")
        lc.configure(bg=C_PANEL, highlightbackground=C_DIM)
        l_text = "◀" if self._show_left_panel else "▶"
        lc.create_text(12, 30, text=l_text, fill=C_PRI, font=font_body_bold(10))

        rc = self._right_toggle
        rc.delete("all")
        rc.configure(bg=C_PANEL, highlightbackground=C_DIM)
        r_text = "▶" if self._show_right_panel else "◀"
        rc.create_text(12, 30, text=r_text, fill=C_PRI, font=font_body_bold(10))

    def _place_layout_widgets(self):
        if getattr(self, "right_slide", 1.0) > 0.05:
            self.log_frame.place(x=self.CHAT_X, y=self.CHAT_Y, width=self.CHAT_W, height=self.CHAT_H)
        else:
            self.log_frame.place_forget()
            
        gap = 12
        mute_w = 126
        pause_w = 126
        shutdown_w = int(self._shutdown_canvas["width"])
        theme_w = int(self._theme_canvas["width"])
        coder_w = int(self._ai_coder_canvas["width"]) if hasattr(self, "_ai_coder_canvas") else 140
        total = mute_w + pause_w + shutdown_w + theme_w + coder_w + gap * 4
        start_x = self.FCX - total // 2
        row1_y = self.CTRL_Y + 20

        self._mute_canvas.place(x=start_x, y=row1_y)
        self._pause_canvas.place(x=start_x + mute_w + gap, y=row1_y)
        self._shutdown_canvas.place(x=start_x + mute_w + pause_w + gap * 2, y=row1_y)
        self._theme_canvas.place(x=start_x + mute_w + pause_w + shutdown_w + gap * 3, y=row1_y)
        if hasattr(self, "_ai_coder_canvas"):
            self._ai_coder_canvas.place(x=start_x + mute_w + pause_w + shutdown_w + theme_w + gap * 4, y=row1_y)

        geo = self._settings_geometry
        panel_x = geo["panel_x"]
        panel_y = geo["panel_y"]
        panel_w = geo["panel_w"]
        panel_h = geo["panel_h"]
        if self._settings_open:
            self._settings_panel.place(x=panel_x, y=panel_y, width=panel_w, height=panel_h)
            self._settings_panel.lift()
            self._settings_title.place(x=14, y=12)
            self._settings_tab_settings.place(x=14, y=40, width=108, height=28)
            self._settings_tab_debug.place(x=130, y=40, width=96, height=28)
            if self._settings_tab == "debug":
                self._settings_body.place_forget()
                self._debug_body.place(x=12, y=76, width=panel_w - 24, height=panel_h - 88)
                self._debug_text.place(x=0, y=0, width=panel_w - 24, height=panel_h - 88)
                self._debug_body.lift()
            else:
                self._debug_body.place_forget()
                self._settings_body.place(x=12, y=76, width=panel_w - 24, height=panel_h - 88)
                self._settings_body.lift()
        else:
            self._settings_panel.place_forget()
            self._settings_title.place_forget()
            self._settings_tab_settings.place_forget()
            self._settings_tab_debug.place_forget()
            self._settings_body.place_forget()
            self._debug_body.place_forget()

        # Place Tools Panel dynamically on top of the "tools" card in left panel
        if self._show_left_panel and not self._settings_open and getattr(self, "left_slide", 1.0) > 0.05:
            x0 = 10
            y0 = HDR_H + 10
            pw = self.LEFT_W - 18
            gap = 14
            total_h = self.H - HDR_H - FOOTER_H - 20
            card_area_h = total_h - gap * 3
            pad = 14
            bw = pw - 2 * pad
            
            cards = [
                ("time", 0.22, "TIME", C_GOLD),
                ("weather", 0.20, "WEATHER · ISTANBUL", C_BLUE),
                ("system", 0.28, "SYSTEM STATUS", C_PRI),
                ("tools", 0.30, "QUICK ACTIONS", C_GREEN),
            ]
            weights = [0.22, 0.20, 0.28, 0.30]
            total_weight = sum(weights)
            heights = [int(card_area_h * (weight / total_weight)) for weight in weights]
            heights[-1] += card_area_h - sum(heights)
            
            current_y = y0
            for (section, _, _, _), ph in zip(cards, heights):
                if section == "tools":
                    # Place the tools panel inside this card
                    section_x = x0 + pad
                    section_pw = bw
                    ty = current_y + 36
                    th = ph - 48
                    self._tools_panel.place(x=section_x + 4, y=ty, width=section_pw - 8, height=th)
                    self._tools_panel.lift()
                current_y += ph + gap
            
            # Place Social Bar dynamically inside the left panel footer area
            self._social_bar.place(x=10 + 14, y=self.H - FOOTER_H - 42, width=self.LEFT_W - 28, height=32)
            self._social_bar.lift()
        else:
            self._tools_panel.place_forget()
            self._social_bar.place_forget()
        if getattr(self, "right_slide", 1.0) > 0.05:
            inp_w = self.CHAT_W - 84
            self._input_entry.place(x=self.CHAT_X, y=self.CHAT_INPUT_Y, width=inp_w, height=INPUT_H)
            self._send_btn.place(x=self.CHAT_X + inp_w + 8, y=self.CHAT_INPUT_Y, width=76, height=INPUT_H)
        else:
            self._input_entry.place_forget()
            self._send_btn.place_forget()

        # Place panel toggles
        lx = self.LEFT_W
        self._left_toggle.place(x=lx, y=self.H//2 - 30)
        
        rx = self.W - self.RIGHT_W - 24 if getattr(self, "right_slide", 1.0) > 0.05 else self.W - 24
        self._right_toggle.place(x=rx, y=self.H//2 - 30)

    def _on_input_submit(self, event=None):
        text = self._input_var.get().strip()
        if not text:
            return
        if self.paused:
            self.write_log("SYS: F.R.I.D.A.Y duraklatılmış durumda. Devam etmek için pause'u kapat.")
            return
        self._input_var.set("")
        if text.lower() in ("sus", "dur", "stop", "sessiz", "kes"):
            self.write_log("SYS: ⏹ Ses kesildi.")
            if self.on_stop_command:
                threading.Thread(target=self.on_stop_command, daemon=True).start()
            return
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    # ── State & callbacks ────────────────────────────────────────────────────
    def set_state(self, state: str):
        previous = getattr(self, "_jarvis_state", "")
        self._jarvis_state = state
        self.speaking = (state == "SPEAKING")
        if state == "THINKING":
            self.sound.start_thinking()
        elif previous == "THINKING":
            self.sound.stop_thinking()
        if state == "ERROR" and previous != "ERROR":
            self.sound.play_error()

    def set_user_speaking(self, value: bool):
        self.mark_user_activity(value)

    def mark_user_activity(self, active: bool = True):
        self.user_speaking = active
        self._user_speaking_until = time.time() + (0.9 if active else 0.0)

    def get_effects_volume(self) -> float:
        return self.sound.get_volume()

    def effects_enabled(self) -> bool:
        return bool(self._effects_active)

    def play_success_sfx(self):
        self.root.after(0, self.sound.play_success)

    def play_error_sfx(self):
        self.root.after(0, self.sound.play_error)

    def focus_panel(self, section: str, duration_ms: int = 4200):
        section = (section or "").strip().lower()
        if not section:
            return

        def _apply():
            self._panel_focus = section
            self._panel_focus_until = time.time() + max(0.8, duration_ms / 1000.0)

        self.root.after(0, _apply)

    def _state_color(self, state: str | None = None) -> str:
        effective = state or self._jarvis_state
        if effective == "PAUSED":
            return C_MID
        return STATE_HEX_COLORS.get(effective, C_PRI)

    @staticmethod
    def _state_badge_text(state: str) -> str:
        if state == "INITIALISING":
            return "CONNECTING"
        if state == "ERROR":
            return "ERROR"
        return "ONLINE"

    # ── Log ──────────────────────────────────────────────────────────────────
    def write_log(self, text: str):
        self.typing_queue.append(text)
        tl = text.lower()
        if tl.startswith("siz:") or tl.startswith("you:"):
            self.mark_user_activity(True)
            self.set_state("THINKING")
        elif tl.startswith("err:") or "error" in tl:
            self._error_hold_until = time.time() + 8.0
            self.set_state("ERROR")
            self.write_debug(text, level="ERROR")
        if not self.is_typing:
            self._start_typing()

    def _start_typing(self):
        if not self.typing_queue:
            self.is_typing = False
            if self._jarvis_state == "ERROR" and time.time() < self._error_hold_until:
                return
            if not self.speaking:
                self.set_state("LISTENING")
            return
        self.is_typing = True
        text = self.typing_queue.popleft()
        tl   = text.lower()
        if   tl.startswith("siz:") or tl.startswith("you:"):   tag = "you"
        elif tl.startswith("jarvis:") or tl.startswith("ai:") or tl.startswith("friday:"): tag = "ai"
        elif tl.startswith("err:") or "error" in tl:           tag = "err"
        else:                                                    tag = "sys"
        self.log_text.configure(state="normal")
        self._type_char(text, 0, tag)

    def _type_char(self, text, i, tag):
        if i < len(text):
            self.log_text.insert(tk.END, text[i], tag)
            self.log_text.see(tk.END)
            self.root.after(7, self._type_char, text, i+1, tag)
        else:
            self.log_text.insert(tk.END, "\n")
            self.log_text.configure(state="disabled")
            self.root.after(20, self._start_typing)

    # ── Stats ────────────────────────────────────────────────────────────────
    def _update_stats(self):
        try:
            self._stats['cpu']  = psutil.cpu_percent()
            self._stats['ram']  = psutil.virtual_memory().percent
            self._stats['disk'] = psutil.disk_usage('/').percent
            batt = psutil.sensors_battery()
            self._stats['battery'] = batt.percent if batt else 100.0
            now = time.time()
            net = psutil.net_io_counters()
            dt  = now - self._last_net_t
            if dt > 0:
                self._stats['net_up']   = max(0, (net.bytes_sent - self._last_net.bytes_sent) / dt / 1024)
                self._stats['net_down'] = max(0, (net.bytes_recv - self._last_net.bytes_recv) / dt / 1024)
            self._last_net   = net
            self._last_net_t = now
            self._cpu_hist.pop(0)
            self._cpu_hist.append(self._stats['cpu'])
        except Exception:
            pass

    # ── Animation loop ───────────────────────────────────────────────────────
    def _animate(self):
        self.tick += 1
        t   = self.tick
        now = time.time()

        # Smooth sliding interpolation
        left_target = 1.0 if self._show_left_panel else 0.0
        right_target = 1.0 if self._show_right_panel else 0.0
        slide_changed = False
        
        if abs(self.left_slide - left_target) > 0.01:
            self.left_slide += (left_target - self.left_slide) * 0.15
            slide_changed = True
        else:
            self.left_slide = left_target
            
        if abs(self.right_slide - right_target) > 0.01:
            self.right_slide += (right_target - self.right_slide) * 0.15
            slide_changed = True
        else:
            self.right_slide = right_target
            
        if slide_changed:
            self._resize_surface(self.W, self.H)

        if self.user_speaking and now > self._user_speaking_until:
            self.user_speaking = False

        if t % 90 == 0:
            threading.Thread(target=self._update_stats, daemon=True).start()
        if t % 1800 == 1:
            self._kick_brief_refresh()

        if self.speaking and t % 3 == 0:
            self._wave_jarvis = [random.randint(6, 30) for _ in range(18)]
        if self.user_speaking and t % 3 == 0:
            self._wave_user = [random.randint(5, 24) for _ in range(18)]

        if now - self.last_t > (0.12 if self.speaking else 0.50):
            if self.paused:
                self.target_scale = random.uniform(0.58, 0.64)
                self.target_halo  = random.uniform(5, 10)
            elif self.speaking:
                self.target_scale = random.uniform(0.98, 1.10)
                self.target_halo  = random.uniform(180, 250)
            elif self.user_speaking:
                self.target_scale = random.uniform(0.88, 0.98)
                self.target_halo  = random.uniform(120, 175)
            elif self._jarvis_state in ("THINKING", "INITIALISING"):
                self.target_scale = random.uniform(0.80, 0.88)
                self.target_halo  = random.uniform(95, 145)
            else:
                self.target_scale = random.uniform(0.72, 0.80)
                self.target_halo  = random.uniform(34, 58)
            self.last_t = now

        sp          = 0.34 if self.speaking else 0.18
        self.scale  += (self.target_scale - self.scale) * sp
        self.halo_a += (self.target_halo   - self.halo_a) * sp

        if self.paused:
            spds = [0.0, 0.0, 0.0, 0.0]
        elif self.speaking:
            spds = [1.6, -1.1, 2.4, -0.7]
        else:
            spds = [0.55, -0.35, 0.90, -0.28]
        for i, spd in enumerate(spds):
            self.rings_spin[i] = (self.rings_spin[i] + spd) % 360

        # Pulse rings
        pspd  = 4.2 if self.speaking else 1.8
        limit = self.FACE * 0.68
        self.pulse_r = [r + pspd for r in self.pulse_r if r + pspd < limit]
        if len(self.pulse_r) < 3 and random.random() < (0.07 if self.speaking else 0.02):
            self.pulse_r.append(0.0)

        for p in self.particles:
            p['x'] = (p['x'] + p['vx']) % self.W
            p['y'] = (p['y'] + p['vy']) % self.H

        if t % 38 == 0:
            self.status_blink = not self.status_blink

        self._draw()
        self.root.after(33, self._animate)

    # ── Yardımcı ─────────────────────────────────────────────────────────────
    @staticmethod
    def _ac(r, g, b, a):
        f = max(0, min(255, int(a))) / 255.0
        return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    def set_user_emotion(self, emotion: str):
        self.user_emotion = emotion.lower()
        self.emotion_expiry = time.time() + 15.0 # keeps the color active for 15 seconds
        self.write_log(f"SYS: Duygu Analizi tetiklendi → {emotion.upper()}")

    def _orb_rgb(self):
        # Empathy Core: check if active emotion has not expired
        if getattr(self, "user_emotion", None) and time.time() < getattr(self, "emotion_expiry", 0.0):
            emotion = self.user_emotion
            if emotion == "tired":
                return (26, 35, 126) # Deep Glowing Blue
            elif emotion == "energetic":
                return (255, 109, 0) # Pulsing Gold/Orange
            elif emotion == "stressed":
                return (213, 0, 249) # Calming Purple/Magenta
            elif emotion == "calm":
                return (0, 229, 255) # Classic Sleek Teal/Turquoise
        
        state = "PAUSED" if self.paused else self._jarvis_state
        return ORB_COLORS.get(state, ORB_COLORS["LISTENING"])

    @staticmethod
    def _split_summary_lines(text: str, limit: int = 4) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return []
        raw = raw.replace(" ve ", ", ")
        parts = [part.strip(" .") for part in raw.split(",") if part.strip()]
        return parts[:limit]

    def _parse_weather_card(self, text: str) -> dict:
        if not text or "alınamadı" in text.lower() or "alınamadi" in text.lower():
            return {
                "city": "Istanbul",
                "primary": "--",
                "details": ["Hava durumu alınamadı."],
            }

        prefix, _, body = text.partition(":")
        city = "Istanbul"
        if " için" in prefix:
            city = prefix.split(" için", 1)[0].strip().title()

        details = [part.strip(" .") for part in body.split(",") if part.strip()]
        primary = "--"
        if details:
            primary = details[0].replace(" derece", "°C")
        return {
            "city": city,
            "primary": primary,
            "details": details[1:4] or ["Anlık veri hazır."],
        }

    def _parse_health_card(self, text: str) -> list[str]:
        if not text or "alınamadı" in text.lower() or "alınamadi" in text.lower():
            return ["Sağlık verisi alınamadı."]
        lines = self._split_summary_lines(text, limit=4)
        return lines or ["Sağlık özeti hazır değil."]

    def _kick_brief_refresh(self):
        if self._brief_refresh_busy:
            return
        self._brief_refresh_busy = True
        threading.Thread(target=self._refresh_brief_cards, daemon=True).start()

    def _refresh_brief_cards(self):
        try:
            weather = get_weather_summary("Istanbul")
            self._weather_card = self._parse_weather_card(weather)
        except Exception:
            self._weather_card = {
                "city": "Istanbul",
                "primary": "--",
                "details": ["Hava durumu alınamadı."],
            }
        finally:
            self._brief_refresh_busy = False

    def _bar(self, c, x, y, w, h, pct, color):
        c.create_rectangle(x, y, x+w, y+h, fill=C_BG, outline=C_DIM, width=1)
        fw = max(1, int(w * pct / 100))
        c.create_rectangle(x+1, y+1, x+fw, y+h-1, fill=color, outline="")

    def _circular_gauge(self, c, x, y, r, pct, color, label=""):
        # Draw background ring
        c.create_oval(x-r, y-r, x+r, y+r, outline=C_BG, width=4)
        # Draw value arc (starts from top 90 deg, extent is negative for clockwise)
        extent = -(pct / 100.0) * 359.9
        c.create_arc(x-r, y-r, x+r, y+r, start=90, extent=extent, outline=color, width=4, style="arc")
        # Center metrics text
        c.create_text(x, y-4, text=f"{pct:.0f}%", fill=C_TEXT, font=font_body_bold(9))
        c.create_text(x, y+9, text=label.upper(), fill=C_MID, font=font_body_bold(7))

    def _sparkline(self, c, x, y, w, h, data):
        c.create_rectangle(x, y, x+w, y+h, fill=C_BG, outline=C_DIM, width=1)
        n = len(data)
        if n < 2:
            return
        step = (w - 2) / (n - 1)
        h2   = h - 2
        coords = []
        for i, v in enumerate(data):
            coords.append(x + 1 + i * step)
            coords.append(y + h - 1 - int(h2 * v / 100))
        c.create_line(*coords, fill=C_PRI, width=1, smooth=True)

    def _bracket(self, c, x0, y0, pw, ph, col=None, bl=12):
        # Köşe parantezleri kaldırıldı (Daha modern görünüm)
        pass

    def _draw_info_card(self, c, x0, y0, pw, ph, title, accent=C_PRI):
        focus = max(0.0, min(1.0, getattr(self, "_card_focus_boost", 0.0)))
        dimmed = bool(getattr(self, "_card_dimmed", False))
        glow = int(55 + 120 * focus)
        border = accent if focus > 0.08 else ("#35504d" if dimmed else self._ac(0, 120, 112, 190))
        fill = C_DIM if dimmed else C_PANEL
        c.create_rectangle(x0, y0, x0+pw, y0+ph, fill=fill, outline="")
        if focus > 0.08:
            for inset in range(3):
                c.create_rectangle(
                    x0-inset, y0-inset, x0+pw+inset, y0+ph+inset,
                    outline=self._ac(*ORB_COLORS["LISTENING"], max(12, glow - inset * 28)),
                    width=1,
                )
        self._bracket(c, x0, y0, pw, ph, col=border, bl=10)
        title_fill = "#6f7d7b" if dimmed else accent
        line_fill = "#173130" if dimmed else C_DIM
        c.create_text(x0+14, y0+14, text=title, fill=title_fill,
                      font=font_display(10), anchor="w")
        c.create_line(x0+12, y0+28, x0+pw-12, y0+28, fill=line_fill)

    def _focus_boost_for(self, section: str) -> float:
        if self._panel_focus != section:
            return 0.0
        remaining = self._panel_focus_until - time.time()
        if remaining <= 0:
            return 0.0
        pulse = 0.65 + 0.35 * math.sin(self.tick * 0.12)
        return min(1.0, remaining / 4.0) * pulse

    # ── Health overlay (sol panel) ────────────────────────────────────────────
    def show_health_hologram(self, query: str, data_str: str):
        def _show():
            self._health_visible = True
            self._health_query   = query.lower()
            self._health_display = data_str
            self._panel_focus = "health"
            self._panel_focus_until = time.time() + 5.0
            if self._health_hide_job:
                self.root.after_cancel(self._health_hide_job)
            self._health_hide_job = self.root.after(14000, self._hide_health_hologram)
        self.root.after(0, _show)

    def _hide_health_hologram(self):
        self._health_visible  = False
        self._health_hide_job = None

    def _draw_health_overlay(self, c):
        x0, y0 = 4, HDR_H + 4
        pw = self.LEFT_W - 8
        ph = self.H - HDR_H - FOOTER_H - 90
        pulse = 0.5 + 0.5 * math.sin(self.tick * 0.08)

        c.create_rectangle(x0, y0, x0+pw, y0+ph,
                           fill="#011510", outline=C_PRI, width=1)
        self._bracket(c, x0, y0, pw, ph, col=C_ORG, bl=10)

        title_col = self._ac(0, 212, 192, int(200 + 55*pulse))
        c.create_text(x0+pw//2, y0+18, text="◈ HEALTH ◈",
                      fill=title_col, font=font_display(11))
        c.create_line(x0+8, y0+30, x0+pw-8, y0+30, fill=C_MID)

        lines = [l for l in self._health_display.split('\n') if l.strip()]
        ly = y0 + 44
        for line in lines:
            if ly > y0 + ph - 14:
                break
            if line.startswith("──"):
                c.create_line(x0+8, ly, x0+pw-8, ly, fill=C_DIM)
                ly += 10
            elif ":" in line:
                parts = line.split(":", 1)
                lbl   = parts[0].strip()
                val   = parts[1].strip() if len(parts) > 1 else ""
                c.create_text(x0+10, ly, text=lbl+":", fill=C_MID,
                              font=font_body(10), anchor="w")
                c.create_text(x0+pw-10, ly, text=val, fill=C_ORG,
                              font=font_body_bold(10), anchor="e")
                ly += 20
            else:
                c.create_text(x0+10, ly, text=line, fill=C_TEXT,
                              font=font_body(9), anchor="w")
                ly += 17

    # ── Sol panel ─────────────────────────────────────────────────────────────
    def _draw_left_panel(self, c):
        if getattr(self, "left_slide", 1.0) < 0.15:
            return
        if self._health_visible:
            self._draw_health_overlay(c)
            return

        x0 = 10
        y0 = HDR_H + 10
        pw = self.LEFT_W - 18
        gap = 14
        total_h = self.H - HDR_H - FOOTER_H - 20
        card_area_h = total_h - gap * 3
        pad = 14
        bw = pw - 2 * pad

        cards = [
            ("time", 0.22, "TIME", C_GOLD),
            ("weather", 0.20, "WEATHER · ISTANBUL", C_BLUE),
            ("system", 0.28, "SYSTEM STATUS", C_PRI),
            ("tools", 0.30, "QUICK ACTIONS", C_GREEN),
        ]
        any_focus_active = bool(self._panel_focus) and (self._panel_focus_until > time.time())
        weights = []
        for section, weight, _, _ in cards:
            weights.append(weight + (0.12 if self._focus_boost_for(section) > 0.08 else 0.0))
        total_weight = sum(weights)
        heights = [int(card_area_h * (weight / total_weight)) for weight in weights]
        heights[-1] += card_area_h - sum(heights)

        current_y = y0
        for (section, _, title, accent), ph in zip(cards, heights):
            focus_boost = self._focus_boost_for(section)
            dimmed = any_focus_active and focus_boost <= 0.08
            shift_x = int(14 * focus_boost)
            extra_w = int(22 * focus_boost)
            section_x = x0 + shift_x
            section_pw = pw + extra_w
            section_pad = pad + int(2 * focus_boost)
            section_bw = section_pw - 2 * section_pad
            muted_label = "#647270" if dimmed else C_MID
            muted_text = "#7e8a88" if dimmed else C_TEXT
            muted_primary = "#8ea19d" if dimmed else C_PRI
            muted_blue = "#829594" if dimmed else C_BLUE
            muted_green = "#85a393" if dimmed else C_GREEN
            muted_gold = "#a1997e" if dimmed else C_GOLD
            muted_warn = "#8d7f77" if dimmed else C_ORG2
            muted_red = "#8a7779" if dimmed else C_RED
            self._card_focus_boost = focus_boost
            self._card_dimmed = dimmed
            self._draw_info_card(c, section_x, current_y, section_pw, ph, title, accent=accent if not dimmed else "#72807f")

            if section == "time":
                c.create_text(section_x+section_pad, current_y+64, text=time.strftime("%H:%M"),
                              fill=muted_primary, font=font_display(36 if focus_boost > 0.08 else 34), anchor="w")
                c.create_text(section_x+section_pad, current_y+92, text=time.strftime(":%S"),
                              fill=muted_label, font=font_body_bold(13), anchor="w")
                c.create_text(section_x+section_pad, current_y+118, text=time.strftime("%d %B %Y").upper(),
                              fill=muted_gold, font=font_body_bold(11), anchor="w")
                c.create_text(section_x+section_pad, current_y+138, text=time.strftime("%A").upper(),
                              fill=muted_text, font=font_body(10), anchor="w")

            elif section == "weather":
                c.create_text(section_x+section_pad, current_y+58, text=self._weather_card["primary"],
                              fill=muted_primary, font=font_display(30 if focus_boost > 0.08 else 28), anchor="w")
                c.create_text(section_x+section_pad, current_y+84, text=self._weather_card["city"].upper(),
                              fill=muted_label, font=font_body_bold(10), anchor="w")
                wy = current_y + 108
                for line in self._weather_card["details"][:3]:
                    c.create_text(section_x+section_pad, wy, text=f"• {line}", fill=muted_text,
                                  font=font_body(10), anchor="w")
                    wy += 17

            elif section == "system":
                cy = current_y + 36
                uptime = int(time.time() - self._started_at)
                up_min, up_sec = divmod(uptime, 60)
                up_hr, up_min = divmod(up_min, 60)
                c.create_text(section_x+section_pad, cy, text=f"UPTIME  {up_hr:02d}:{up_min:02d}:{up_sec:02d}",
                              fill=muted_label, font=font_body_bold(9), anchor="w")
                
                # 2x2 Circular Gauges
                gauges = [
                    ("CPU", "cpu", section_x + section_pw // 4, current_y + 78),
                    ("RAM", "ram", section_x + (section_pw * 3) // 4, current_y + 78),
                    ("DISK", "disk", section_x + section_pw // 4, current_y + 144),
                    ("BATTERY", "battery", section_x + (section_pw * 3) // 4, current_y + 144)
                ]
                
                for label, key, gx, gy in gauges:
                    val = self._stats[key]
                    col = C_RED if val > 80 and key != "battery" else C_ORG if val > 55 and key != "battery" else (C_RED if key == "battery" and val < 20 else C_GREEN if key == "battery" else C_PRI)
                    if dimmed:
                        col = muted_red if col == C_RED else muted_warn if col == C_ORG else muted_green if col == C_GREEN else muted_primary
                    self._circular_gauge(c, gx, gy, 24, val, col, label)

                up = self._stats["net_up"]
                down = self._stats["net_down"]
                up_s = f"{up:.1f} KB/s" if up < 1000 else f"{up/1024:.1f} MB/s"
                down_s = f"{down:.1f} KB/s" if down < 1000 else f"{down/1024:.1f} MB/s"
                
                # Bottom network details
                net_y = current_y + ph - 24
                c.create_line(section_x+section_pad, net_y-4, section_x+section_pw-section_pad, net_y-4, fill="#173130" if dimmed else C_DIM)
                c.create_text(section_x+section_pad, net_y+8, text=f"▲ {up_s}", fill=muted_warn, font=font_body(9), anchor="w")
                c.create_text(section_x+section_pw-section_pad, net_y+8, text=f"▼ {down_s}", fill=muted_green, font=font_body(9), anchor="e")

            elif section == "tools":
                pass

            current_y += ph + gap

        self._card_focus_boost = 0.0
        self._card_dimmed = False

    # ── Sağ panel ─────────────────────────────────────────────────────────────
    def _draw_right_panel(self, c):
        if getattr(self, "right_slide", 1.0) < 0.15:
            return
        x0  = self.CHAT_PANEL_X
        y0  = self.CHAT_PANEL_Y
        pw  = self.CHAT_PANEL_W
        ph  = self.CHAT_PANEL_H
        pad = 10

        c.create_rectangle(x0, y0, x0+pw, y0+ph, fill=C_PANEL, outline="")
        self._bracket(c, x0, y0, pw, ph, col=C_MID)

        if self.paused:
            sc, st = C_MID, "PAUSED"
        else:
            sc, st = self._state_color(self._jarvis_state), self._jarvis_state

        c.create_text(x0+14, y0+16, text="CONVERSATION", fill=C_PRI,
                      font=font_display(11), anchor="w")
        c.create_text(x0+pw-pad, y0+16, text=st, fill=sc,
                      font=font_body_bold(10), anchor="e")
        c.create_line(x0+pad, y0+28, x0+pw-pad, y0+28, fill=C_DIM)

    # ── ORB (ana çizim) ───────────────────────────────────────────────────────
    def _draw_orb(self, c):
        state = "PAUSED" if self.paused else self._jarvis_state
        t    = self.tick
        speak_pulse = 1.0
        if self.speaking:
            speak_pulse = 1.0 + 0.12 * math.sin(t * 0.23) + 0.05 * math.sin(t * 0.11 + 1.2)
        elif self.user_speaking:
            speak_pulse = 1.0 + 0.06 * math.sin(t * 0.18 + 0.7)
        elif state in ("THINKING", "INITIALISING"):
            speak_pulse = 1.0 + 0.03 * math.sin(t * 0.10)
        else:
            speak_pulse = 1.0 + 0.01 * math.sin(t * 0.07)

        move_x = 0
        move_y = 0
        if self.user_speaking:
            move_x = int(6 * math.sin(t * 0.06))
            move_y = int(4 * math.cos(t * 0.09 + 0.5))
        elif state in ("THINKING", "INITIALISING"):
            move_x = int(3 * math.sin(t * 0.045))
            move_y = int(2 * math.cos(t * 0.05 + 0.4))

        FCX  = self.FCX + move_x
        FCY  = self.FCY + move_y
        FW   = int(self.FACE * self.scale * speak_pulse)
        R, G, B = self._orb_rgb()
        ha   = self.halo_a
        field_r = int(FW * 0.49)
        inner_r = int(FW * 0.34)
        activity = (
            0.10 if self.paused else
            1.00 if self.speaking else
            0.78 if self.user_speaking else
            0.62 if state in ("THINKING", "INITIALISING") else
            0.26
        )
        if state in ("THINKING", "INITIALISING"):
            accent_rgb = (255, 210, 72)
        elif self.speaking:
            accent_rgb = (170, 220, 255)
        elif self.user_speaking:
            accent_rgb = (118, 200, 255)
        else:
            accent_rgb = (120, 255, 185)

        # Pulse rings
        for pr in self.pulse_r:
            alpha = max(0, int(160 * (1.0 - pr / (FW * 0.70))))
            rr = int(pr + field_r * 0.96)
            c.create_oval(
                FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                outline=self._ac(R, G, B, alpha),
                width=1,
            )

        # Large outer glow
        if not self.paused:
            for i in range(10, 0, -1):
                frac = i / 10
                rr = int(field_r * (1.02 + 0.045 * frac))
                alpha = int(ha * 0.10 * frac)
                if self.speaking:
                    ox = 0
                    oy = 0
                else:
                    ox = int(3 * math.sin(t * 0.010 + i))
                    oy = int(3 * math.cos(t * 0.009 + i * 1.3))
                c.create_oval(
                    FCX-rr+ox, FCY-rr+oy, FCX+rr+ox, FCY+rr+oy,
                    outline=self._ac(R, G, B, alpha),
                    width=3,
                )

        # Structural circles
        for frac, width, alpha_mult in (
            (1.00, 2, 0.34),
            (0.90, 2, 0.24),
            (0.76, 1, 0.18),
            (0.62, 1, 0.12),
        ):
            rr = int(field_r * frac)
            c.create_oval(
                FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                outline=self._ac(R, G, B, int(ha * alpha_mult * (0.4 if self.paused else 1.0))),
                width=width,
            )

        speak_shell_push = 1.16 if self.speaking else 1.07 if self.user_speaking else 1.0
        # Orb shell particles
        shell_r = field_r * 0.93 * speak_shell_push
        for idx, sp in enumerate(self.orb_shell_particles):
            angle = sp['angle'] + t * sp['speed'] * (2.8 if self.speaking else 1.6 if self.user_speaking else 1.1)
            wobble = 1.0 + (0.07 if self.speaking else 0.035) * math.sin(t * 0.08 + sp['phase'])
            x = FCX + math.cos(angle) * shell_r * wobble
            y = FCY + math.sin(angle) * shell_r * wobble
            alpha = int((70 + 120 * sp['glow']) * (0.26 if self.paused else 0.52 + activity * 0.45))
            if idx % 9 == 0 and not self.paused:
                col = self._ac(accent_rgb[0], accent_rgb[1], accent_rgb[2], min(255, alpha + 30))
            else:
                col = self._ac(R, G, B, alpha)
            pr = sp['size'] * (1.0 + 0.24 * math.sin(t * 0.05 + sp['phase']))
            c.create_oval(x-pr, y-pr, x+pr, y+pr, fill=col, outline="")

        # Rotating segmented arcs
        arc_r1 = int(field_r * 0.96)
        arc_r2 = int(field_r * 0.78)
        for start, extent, width, accent in (
            (self.rings_spin[0], 52 if self.speaking else 34, 3, False),
            ((self.rings_spin[0] + 148) % 360, 26, 2, True),
            ((self.rings_spin[2] + 28) % 360, 64 if self.user_speaking else 40, 3, False),
            ((self.rings_spin[2] + 212) % 360, 18, 2, True),
        ):
            rr = arc_r1 if width == 3 else arc_r2
            if accent and not self.paused:
                col = self._ac(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(120 + 80 * activity))
            else:
                col = self._ac(R, G, B, int(ha * (1.2 if width == 3 else 0.7)))
            c.create_arc(
                FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                start=start, extent=extent,
                outline=col, width=width, style="arc",
            )

        # Particle orb field
        field_limit = inner_r * (
            0.82 if self.paused else
            1.36 if self.speaking else
            1.16 if self.user_speaking else
            1.0
        )
        for idx, p in enumerate(self.orb_particles):
            speed_mult = (
                0.10 if self.paused else
                3.10 if self.speaking else
                2.00 if self.user_speaking else
                1.10
            )
            angle = p['angle'] + t * p['speed'] * speed_mult
            wobble = 1.0 + (0.30 if self.speaking else 0.18) * math.sin(t * p['wobble'] + p['phase'])
            orbit = field_limit * p['orbit'] * wobble
            depth = 0.5 + 0.5 * math.sin(angle * 2.0 + t * 0.013 + p['phase'])
            y_squash = 0.62 + depth * 0.38
            drift = (8.0 if self.speaking else 5.0 if self.user_speaking else 4.0) * p['depth']
            x = FCX + math.cos(angle) * orbit + math.sin(t * 0.011 + p['phase']) * drift
            y = FCY + math.sin(angle) * orbit * y_squash + math.cos(t * 0.010 + p['phase']) * drift
            base_alpha = int((18 + 155 * p['depth']) * (0.24 + activity * 0.86) * (0.45 + depth * 0.75))
            if self.paused:
                base_alpha = int(base_alpha * 0.40)
            if idx % 11 == 0 and not self.paused:
                col = self._ac(accent_rgb[0], accent_rgb[1], accent_rgb[2], min(255, base_alpha + 25))
            elif self.user_speaking and idx % 7 == 0:
                col = self._ac(120, 205, 255, min(255, base_alpha + 20))
            else:
                col = self._ac(R, G, B, base_alpha)
            pr = p['size'] * (0.70 if self.paused else 0.90 + depth * 0.65 + 0.30 * activity * p['depth'])
            c.create_oval(x-pr, y-pr, x+pr, y+pr, fill=col, outline="")
            if idx % 18 == 0 and not self.paused:
                c.create_line(
                    FCX + (x-FCX) * 0.18,
                    FCY + (y-FCY) * 0.18,
                    x, y,
                    fill=self._ac(R, G, B, int(18 + 35 * p['depth'] * activity)),
                    width=1,
                )

        # Center void keeps the orb airy instead of lens-like.
        void_r = int(inner_r * (0.18 if self.paused else 0.12))
        if void_r > 0:
            c.create_oval(
                FCX-void_r, FCY-void_r, FCX+void_r, FCY+void_r,
                fill=C_BG,
                outline="",
            )

        # Holographic Spotify/Audio Spectrum Visualizer Ring
        from actions.camera_vision import is_gesture_active
        gest_active = is_gesture_active()
        
        num_bars = 32
        base_angle_step = math.tau / num_bars
        for i in range(num_bars):
            angle = i * base_angle_step + t * 0.006
            
            # Dinamik genlik hesabı (Speaking, User Speaking, Gesture Active veya Ambient durumları)
            if self.speaking:
                amp = 0.45 + 0.40 * math.sin(t * 0.22 + i * 0.7) + 0.15 * math.sin(t * 0.09 + i * 1.3)
            elif self.user_speaking:
                amp = 0.30 + 0.25 * math.sin(t * 0.18 + i * 0.9)
            elif gest_active:
                amp = 0.20 + 0.15 * math.sin(t * 0.11 + i * 0.5)
            else:
                amp = 0.15 + 0.10 * math.sin(t * 0.08 + i * 0.4)
                
            noise = max(0.0, amp * random.uniform(0.75, 1.25))
            r_start = int(field_r * 1.05)
            r_end = int(field_r * (1.05 + 0.32 * noise))
            
            x1 = FCX + math.cos(angle) * r_start
            y1 = FCY + math.sin(angle) * r_start
            x2 = FCX + math.cos(angle) * r_end
            y2 = FCY + math.sin(angle) * r_end
            
            alpha = int(70 + 155 * noise)
            col = self._ac(R, G, B, alpha)
            c.create_line(x1, y1, x2, y2, fill=col, width=2)

        # --- NEW: Holographic Avatar Overlays ---
        # 1. Corner Brackets around the Orb
        box_r = int(field_r * 1.5)
        self._bracket(c, FCX - box_r, FCY - box_r, box_r * 2, box_r * 2, col=C_PRI, bl=20)
        
        # 2. Outer Rotating Ring with ticks
        outer_r = int(field_r * 1.4)
        c.create_oval(FCX - outer_r, FCY - outer_r, FCX + outer_r, FCY + outer_r, outline=self._ac(R, G, B, 40), width=1)
        
        # 3. Ticks on the outer ring
        for i in range(0, 360, 15):
            angle = math.radians(i + t * 0.5)
            x1 = FCX + math.cos(angle) * outer_r
            y1 = FCY + math.sin(angle) * outer_r
            x2 = FCX + math.cos(angle) * (outer_r + 5)
            y2 = FCY + math.sin(angle) * (outer_r + 5)
            c.create_line(x1, y1, x2, y2, fill=self._ac(R, G, B, 80), width=1)
            
        # 4. Crosshairs
        c.create_line(FCX - field_r * 0.2, FCY, FCX + field_r * 0.2, FCY, fill=self._ac(R, G, B, 100), width=1)
        c.create_line(FCX, FCY - field_r * 0.2, FCX, FCY + field_r * 0.2, fill=self._ac(R, G, B, 100), width=1)
        
        # 5. Status Text near the Orb
        status_text = f"AVATAR CORE: {state}"
        c.create_text(FCX, FCY + box_r + 15, text=status_text, fill=C_PRI, font=font_display(9))

    # ── Ana çizim ─────────────────────────────────────────────────────────────
    def _draw(self):
        c  = self.bg
        W  = self.W
        H  = self.H
        t  = self.tick
        c.delete("all")

        # ── Arka plan ────────────────────────────────────────────────────────
        # Fütüristik Nokta ve Artı (+) Izgarası
        step = 64
        for x in range(0, W, step):
            for y in range(0, H, step):
                # Her grid kesişiminde küçük siber artı (+) veya nokta çizimi
                if (x // step) % 2 == 0 and (y // step) % 2 == 0:
                    c.create_line(x-3, y, x+3, y, fill=C_DIM, width=1)
                    c.create_line(x, y-3, x, y+3, fill=C_DIM, width=1)
                else:
                    c.create_rectangle(x, y, x+1, y+1, fill=C_DIMMER, outline="")

        # Central Dynamic Glowing Backdrop (Yapay Zeka Core Çevresine Yayılan Ambient Işık)
        R, G, B = self._orb_rgb()
        glow_base_r = int(self.FACE * 0.8 * self.scale)
        for i in range(5, 0, -1):
            gr = int(glow_base_r * (1.0 + i * 0.22))
            alpha = int(self.halo_a * 0.15 * (1.0 - i * 0.18))
            if alpha > 0:
                c.create_oval(self.FCX-gr, self.FCY-gr, self.FCX+gr, self.FCY+gr,
                              fill="", outline=self._ac(R, G, B, alpha), width=1)

        # Sentinel Cyberpunk Radar Sweep Overlay
        from actions.camera_vision import is_sentinel_active, is_gesture_active
        sentinel_on = is_sentinel_active()
        gesture_on = is_gesture_active()

        if sentinel_on:
            radar_r = int(self.FACE * 1.35 * self.scale)
            # Sonar rings
            for r_offset in (0.7, 0.9, 1.1):
                rr = int(radar_r * r_offset)
                c.create_oval(self.FCX-rr, self.FCY-rr, self.FCX+rr, self.FCY+rr,
                              fill="", outline=self._ac(255, 23, 68, 42), width=1)
            # Sweeper line
            sweep_angle = (t * 2.2) % 360
            rad = math.radians(sweep_angle)
            rx = self.FCX + math.cos(rad) * radar_r * 1.15
            ry = self.FCY + math.sin(rad) * radar_r * 1.15
            c.create_line(self.FCX, self.FCY, rx, ry, fill="#ff1744", width=2)
            c.create_arc(self.FCX - radar_r, self.FCY - radar_r, self.FCX + radar_r, self.FCY + radar_r,
                         start=-sweep_angle, extent=45, fill="", outline="#f43f5e", width=1, style="arc")
            # Flashing security text - Daha modern ve şık
            c.create_text(self.FCX, self.FCY - radar_r - 18, text="SYSTEM LOCKED // SENTINEL ACTIVE", fill="#f43f5e", font=font_body_bold(9))

        # Gesture Cyberpunk Indicator Outer Rings
        if gesture_on:
            gest_r = int(self.FACE * 1.55 * self.scale)
            # Spinning outer green arcs to show gesture ready status
            c.create_arc(self.FCX - gest_r, self.FCY - gest_r, self.FCX + gest_r, self.FCY + gest_r,
                         start=(t * 1.8) % 360, extent=70, fill="", outline="#00ff88", width=2, style="arc")
            c.create_arc(self.FCX - gest_r, self.FCY - gest_r, self.FCX + gest_r, self.FCY + gest_r,
                         start=((t * 1.8) + 180) % 360, extent=70, fill="", outline="#00ff88", width=2, style="arc")
            c.create_text(self.FCX, self.FCY + gest_r + 18, text="🖐️ GESTURE SYSTEM ONLINE", fill="#00ff88", font=font_body_bold(8))

        # Siber Teknik Koordinat Etiketleri ve Tarama çizgisi kaldırıldı (Daha modern görünüm)

        # Partiküller & Siber Bağlantı (Constellation/Neural Network) Efekti
        num_p = len(self.particles)
        for i in range(num_p):
            p1 = self.particles[i]
            for j in range(i+1, num_p):
                p2 = self.particles[j]
                dist = math.hypot(p1['x'] - p2['x'], p1['y'] - p2['y'])
                if dist < 110:
                    alpha_conn = int((1.0 - dist / 110) * 15 * (1.5 if self.speaking else 0.8))
                    c.create_line(p1['x'], p1['y'], p2['x'], p2['y'],
                                  fill=self._ac(R, G, B, alpha_conn), width=1)

        for p in self.particles:
            if self.speaking:
                col = self._ac(255, 110, 0, p['a'])
            else:
                col = self._ac(R, G, B, p['a'])
            r = p['r']
            c.create_oval(p['x']-r, p['y']-r, p['x']+r, p['y']+r,
                          fill=col, outline="")

        # ── Bölücü çizgiler (ince, soluk) ────────────────────────────────────
        if self._show_left_panel:
            c.create_line(self.LEFT_W, HDR_H, self.LEFT_W, H-FOOTER_H,
                          fill=C_DIM, width=1)
        if self._show_right_panel:
            c.create_line(W-self.RIGHT_W, HDR_H, W-self.RIGHT_W, H-FOOTER_H,
                          fill=C_DIM, width=1)

        # ── Yan paneller ──────────────────────────────────────────────────────
        if self._show_left_panel:
            self._draw_left_panel(c)
        if self._show_right_panel:
            self._draw_right_panel(c)

        # ── Orb ──────────────────────────────────────────────────────────────
        self._draw_orb(c)

        state_label = "PAUSED" if self.paused else self._jarvis_state
        state_col = self._state_color(state_label)
        c.create_text(self.FCX, self.CTRL_Y - 34, text=SYSTEM_NAME,
                      fill=C_TEXT, font=font_display(18))
        c.create_text(self.FCX, self.CTRL_Y - 12, text=f"● {state_label.title()}",
                      fill=state_col, font=font_body_bold(11))

        # ── HEADER ───────────────────────────────────────────────────────────
        c.create_rectangle(0, 0, W, HDR_H, fill=C_BG, outline="")
        # Alt çizgi — teal parlak
        c.create_line(0, HDR_H, W, HDR_H, fill=C_MID, width=1)
        for i in range(3):
            a = 60 - i * 18
            c.create_line(0, HDR_H-1-i, W, HDR_H-1-i,
                          fill=self._ac(99, 102, 241, a), width=1) # Indigo parlama

        # Büyük başlık kaldırıldı (Kullanıcı talebi)

        # Sol: model badge ve koruma/jest indikatörleri (Dinamik import ile dairesel import engellenir)
        from actions.camera_vision import is_sentinel_active, is_gesture_active
        sentinel_on = is_sentinel_active()
        gesture_on = is_gesture_active()

        c.create_text(22, 20, text=MODEL_BADGE,
                      fill=C_DIM, font=font_body(9), anchor="w")

        # Sentinel Modu Pill Badge
        s_fill = "#4c0519" if sentinel_on else C_PANEL # Rose-900 veya Panel
        s_txt = "🛡️ SENTINEL ACTIVE" if sentinel_on else "🛡️ SENTINEL STANDBY"
        s_col = "#f43f5e" if sentinel_on else C_DIM # Rose veya Dim
        c.create_rectangle(22, 36, 158, 56, fill=s_fill, outline=s_col, width=1)
        c.create_text(90, 46, text=s_txt, fill="#ffe4e6" if sentinel_on else "#64748b", font=font_body_bold(8))

        # Gesture Control Pill Badge
        g_fill = "#052e16" if gesture_on else C_PANEL # Green-900 veya Panel
        g_txt = "🖐️ GESTURE ACTIVE" if gesture_on else "🖐️ GESTURE STANDBY"
        g_col = "#10b981" if gesture_on else C_DIM # Emerald veya Dim
        c.create_rectangle(168, 36, 304, 56, fill=g_fill, outline=g_col, width=1)
        c.create_text(236, 46, text=g_txt, fill="#d1fae5" if gesture_on else "#64748b", font=font_body_bold(8))

        # Coder Mode Pill Badge (Otonom Proje Geliştirici Durumu)
        c_fill = "#1e1b4b" # Koyu Indigo Panel
        c_txt = "💻 CODER READY"
        c_col = C_PRI
        c.create_rectangle(314, 36, 450, 56, fill=c_fill, outline=c_col, width=1)
        c.create_text(382, 46, text=c_txt, fill="#e0e7ff", font=font_body_bold(8))

        # Sağ: durum indikatörü
        indicator_state = "PAUSED" if self.paused else self._jarvis_state
        ind_col = self._state_color(indicator_state)
        indicator_text = self._state_badge_text(indicator_state)
        sym = "●" if self.status_blink else "○"
        c.create_text(W-22, 36, text=f"{sym}  {indicator_text}",
                      fill=ind_col, font=font_body_bold(11), anchor="e")

        # ── FOOTER ───────────────────────────────────────────────────────────
        c.create_rectangle(0, H-FOOTER_H, W, H, fill=C_BG, outline="")
        c.create_line(0, H-FOOTER_H, W, H-FOOTER_H, fill=C_DIM, width=1)
        c.create_text(W//2, H-13, fill=C_DIM, font=font_body(9),
                      text="F.R.I.D.A.Y · Windows Edition · Realtime Voice Core")
        c.create_text(W-18, H-13, fill=C_DIM, font=font_body(9),
                      text="[ ] TOGGLE PANELS  [F4] MUTE  [F5] PAUSE  [ESC] EXIT", anchor="e")
        
        # Arka plan tuvalini (canvas) en alta al ki tüm native pencereler (toggles, buttons, entries) tıklanabilsin!
        self.bg.tk.call('lower', self.bg._w)


    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    def _show_setup_ui(self, edit_mode: bool = False):
        self._close_setup_ui()

        self.setup_frame = tk.Frame(self.root, bg=C_PANEL,
                                    highlightbackground=C_PRI,
                                    highlightthickness=1)
        setup_w = min(760, max(560, int(self.W * 0.42)))
        setup_h = min(540, max(450, int(self.H * 0.46)))
        self.setup_frame.place(relx=0.5, rely=0.5, anchor="center", width=setup_w, height=setup_h)
        self.setup_frame.pack_propagate(False)

        title = "◈ API AYARLARI" if edit_mode else "◈ İLK KURULUM GEREKLİ"
        subtitle = (
            "Gemini ve YouTube ayarlarınızı güncelleyin."
            if edit_mode else
            "Gemini API anahtarınızı girin. YouTube alanları opsiyoneldir."
        )
        config = load_app_config()

        tk.Label(self.setup_frame, text=title,
                 fg=C_PRI, bg=C_PANEL, font=font_display(18)).pack(pady=(24, 6))
        tk.Label(self.setup_frame, text=subtitle,
                 fg=C_MUTED, bg=C_PANEL, font=font_body(11)).pack(pady=(0, 16))
        
        tk.Label(self.setup_frame, text="GEMINI API ANAHTARI",
                 fg=C_PRI, bg=C_PANEL, font=font_body_bold(10)).pack(pady=(8, 4))

        self.api_entry = tk.Entry(
            self.setup_frame, width=54,
            fg=C_TEXT, bg=C_BG, insertbackground=C_TEXT,
            borderwidth=0, highlightthickness=1, highlightcolor=C_PRI, highlightbackground=C_MID,
            font=font_body(11), show="*")
        self.api_entry.pack(pady=(0, 8), ipady=5)

        current_key = str(config.get("gemini_api_key", "") or "")
        if current_key:
            self.api_entry.insert(0, current_key)

        tk.Label(self.setup_frame, text="YOUTUBE API ANAHTARI",
                 fg=C_PRI, bg=C_PANEL, font=font_body_bold(10)).pack(pady=(10, 4))

        self.youtube_api_entry = tk.Entry(
            self.setup_frame, width=54,
            fg=C_TEXT, bg=C_BG, insertbackground=C_TEXT,
            borderwidth=0, highlightthickness=1, highlightcolor=C_PRI, highlightbackground=C_MID,
            font=font_body(11), show="*")
        self.youtube_api_entry.pack(pady=(0, 8), ipady=5)
        current_youtube_key = str(config.get("youtube_api_key", "") or "")
        if current_youtube_key:
            self.youtube_api_entry.insert(0, current_youtube_key)

        tk.Label(self.setup_frame, text="YOUTUBE KANAL ADI (HANDLE / CHANNEL)",
                 fg=C_PRI, bg=C_PANEL, font=font_body_bold(10)).pack(pady=(10, 4))

        self.youtube_handle_entry = tk.Entry(
            self.setup_frame, width=54,
            fg=C_TEXT, bg=C_BG, insertbackground=C_TEXT,
            borderwidth=0, highlightthickness=1, highlightcolor=C_PRI, highlightbackground=C_MID,
            font=font_body(11))
        self.youtube_handle_entry.pack(pady=(0, 8), ipady=5)
        current_handle = str(config.get("youtube_channel_handle", "") or "")
        if current_handle:
            self.youtube_handle_entry.insert(0, current_handle)

        buttons = tk.Frame(self.setup_frame, bg=C_PANEL)
        buttons.pack(pady=16)

        tk.Button(buttons, text="▸ KAYDET",
                  command=self._save_api_key, bg=C_PRI, fg=C_BG,
                  activebackground=C_ORG, activeforeground=C_TEXT, font=font_body_bold(11),
                  borderwidth=0, padx=28, pady=8, cursor="hand2", relief="flat").pack(side="left", padx=8)

        if edit_mode:
            tk.Button(buttons, text="KAPAT",
                      command=self._close_setup_ui, bg=C_DIM, fg=C_TEXT,
                      activebackground=C_MID, activeforeground=C_TEXT, font=font_body_bold(11),
                      borderwidth=0, padx=28, pady=8, cursor="hand2", relief="flat").pack(side="left", padx=8)

    def _save_api_key(self):
        was_ready = self._api_key_ready
        key = self.api_entry.get().strip() if self.api_entry else ""
        if not key:
            return
        youtube_key = self.youtube_api_entry.get().strip() if self.youtube_api_entry else ""
        youtube_handle = self.youtube_handle_entry.get().strip() if self.youtube_handle_entry else ""
        save_app_config(
            {
                "gemini_api_key": key,
                "youtube_api_key": youtube_key,
                "youtube_channel_handle": youtube_handle,
                "voice": self._current_voice,
            }
        )
        self._close_setup_ui()
        self._api_key_ready = True
        self._refresh_settings_status()
        if was_ready:
            self.write_log("SYS: API ayarlari guncellendi.")
        else:
            self.set_state("LISTENING")
            self.write_log("SYS: F.R.I.D.A.Y hazır. Dinliyorum...")

    def show_lock_screen(self):
        if hasattr(self, "lock_frame") and self.lock_frame.winfo_exists():
            return

        self.lock_frame = tk.Frame(self.root, bg=C_BG)
        self.lock_frame.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.lock_frame.lift()
        
        self.lock_container = tk.Frame(self.lock_frame, bg=C_BG)
        self.lock_container.place(relx=0.5, rely=0.5, anchor="center")
        
        self.lock_canvas = tk.Canvas(self.lock_container, width=180, height=180, bg=C_BG, highlightthickness=0)
        self.lock_canvas.pack(pady=(0, 20))
        
        self._lock_pulse = 0.0
        self._unlocked = False
        
        self.lock_label = tk.Label(
            self.lock_container, 
            text="SİSTEM KİLİTLİ",
            fg="#f43f5e", bg=C_BG, font=font_display(22), justify="center"
        )
        self.lock_label.pack(pady=(0, 4))
        
        self.lock_sublabel = tk.Label(
            self.lock_container,
            text="Lütfen yetkili RFID kimliğinizi tarayıcıya yaklaştırın...",
            fg=C_MUTED, bg=C_BG, font=font_body(11), justify="center"
        )
        self.lock_sublabel.pack()

        # Fütüristik Bypass/Simülasyon Butonu (Donanım bağlı olmadığında can kurtaran!)
        bypass_btn = tk.Button(
            self.lock_container,
            text="🔑 KARTIM YOK (SİMÜLE KART OKUT)",
            fg=C_GOLD, bg=C_PANEL, activeforeground=C_BG, activebackground=C_GOLD,
            font=font_body_bold(10), borderwidth=0, highlightthickness=1,
            highlightbackground=C_MID, cursor="hand2", padx=24, pady=10,
            command=self._simulate_card_scan
        )
        bypass_btn.pack(pady=(28, 0))
        
        # Yumuşak neon geçiş efektleri
        bypass_btn.bind("<Enter>", lambda e: bypass_btn.configure(fg=C_BG, bg=C_GOLD))
        bypass_btn.bind("<Leave>", lambda e: bypass_btn.configure(fg=C_GOLD, bg=C_PANEL))

        self._animate_lock_screen()

    def _simulate_card_scan(self):
        if self.on_rfid_bypass:
            self.on_rfid_bypass()
        self.unlock_screen()

    def _animate_lock_screen(self):
        if not hasattr(self, "lock_frame") or not self.lock_frame.winfo_exists():
            return
            
        self._lock_pulse += 0.06
        state = "green" if self._unlocked else "red"
        self._draw_lock_icon(state)
        
        self.root.after(30, self._animate_lock_screen)

    def _draw_lock_icon(self, state="red"):
        if not hasattr(self, "lock_canvas") or not self.lock_canvas.winfo_exists():
            return
            
        self.lock_canvas.delete("all")
        color = "#f43f5e" if state == "red" else "#10b981" # Rose ve Emerald
        cx, cy = 90, 90
        
        # Dış fütüristik kesikli radar çemberi (hızla döner ve genişler)
        rot_offset = self._lock_pulse * 1.5
        for i in range(4):
            start_ang = (i * 90 + rot_offset * 15) % 360
            self.lock_canvas.create_arc(cx - 75, cy - 75, cx + 75, cy + 75,
                                         start=start_ang, extent=55, style=tk.ARC, outline=color, width=2.5)
        
        # İç sabit çember
        self.lock_canvas.create_oval(cx - 55, cy - 55, cx + 55, cy + 55, outline=color, width=1.5)
        
        # RFID Kart Tasarımı
        card_w, card_h = 28, 42
        self.lock_canvas.create_rectangle(cx - card_w, cy - card_h, cx + card_w, cy + card_h,
                                          fill="#0f172a", outline=color, width=2.5)
        
        # Temassız bağlantı dalgaları (card icon inside)
        for r in (10, 18, 26):
            self.lock_canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                         start=-45, extent=90, style=tk.ARC, outline=color, width=2)
                                         
        # Aşağı yukarı hareket eden Lazer Tarayıcı (Scanline) ve Kıvılcımlar
        if state == "red":
            sweep_y = cy - card_h + 4 + (math.sin(self._lock_pulse * 3.5) * 0.5 + 0.5) * (card_h * 2 - 8)
            # Lazer ana çizgisi
            self.lock_canvas.create_line(cx - card_w + 3, sweep_y, cx + card_w - 3, sweep_y, fill=color, width=2.5)
            # Lazer parlaması (yarı saydam)
            self.lock_canvas.create_line(cx - card_w - 1, sweep_y, cx + card_w + 1, sweep_y, fill=self._ac(244, 63, 94, 60), width=5)
            
            # --- FÜTÜRİSTİK PARILDAYAN KIVILCIMLAR ---
            # Pulse değerine göre istikrarlı ama rastgele kayan parçacıklar üret
            random.seed(int(self._lock_pulse * 10))
            for _ in range(6):
                px = cx + random.uniform(-card_w + 5, card_w - 5)
                py = sweep_y + random.uniform(-3, 3)
                pr = random.uniform(1.2, 2.8)
                alpha = random.randint(110, 255)
                self.lock_canvas.create_oval(px - pr, py - pr, px + pr, py + pr,
                                             fill=self._ac(244, 63, 94, alpha), outline="")
        else:
            # Yeşil kilit açılma taraması (Ortada sabit parlar)
            self.lock_canvas.create_line(cx - card_w + 3, cy, cx + card_w - 3, cy, fill=color, width=3.5)
            self.lock_canvas.create_line(cx - card_w - 1, cy, cx + card_w + 1, cy, fill=self._ac(16, 185, 129, 80), width=6)

    def unlock_screen(self):
        if not hasattr(self, "lock_frame") or not self.lock_frame.winfo_exists():
            return
            
        self._unlocked = True
        self._draw_lock_icon("green")
        self.lock_label.configure(text="ERİŞİM SAĞLANDI", fg="#10b981")
        self.lock_sublabel.configure(text="Sistem başarıyla açıldı. Hoş geldiniz...", fg="#10b981")
        
        self.root.after(2000, self._cleanup_lock)

    def _cleanup_lock(self):
        self._unlocked = False
        if hasattr(self, "lock_frame") and self.lock_frame.winfo_exists():
            self.lock_frame.destroy()
