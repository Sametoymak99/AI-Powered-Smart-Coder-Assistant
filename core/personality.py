import logging
from typing import Dict, Any, List

logger = logging.getLogger("PersonalitySystem")

class PersonalitySystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PersonalitySystem, cls).__new__(cls)
            cls._instance._init_personality()
        return cls._instance

    def _init_personality(self):
        self.PERSONALITY_MODES = {
            "teknik": {
                "tone": "formal",
                "use_emoji": False,
                "verbose": True,
                "greeting": "F.R.I.D.A.Y. NEXUS Sistemleri devrede. Tüm veriler nominal.",
                "style_hint": "Yanıtlarında tamamen teknik detaylar, kod örnekleri, performans ölçümleri ve sistem analizi bilgilerine yer veriyorsun. Asla lafı uzatma, net ve mühendislik diliyle konuş."
            },
            "arkadas": {
                "tone": "casual",
                "use_emoji": True,
                "verbose": False,
                "greeting": "Selam dostum! Bugün ne yapıyoruz? Buralar benden sorulur. 😎",
                "style_hint": "Samimi, enerjik, arkadaşça ve bol emojili konuşuyorsun. Kullanıcıya destekleyici ve cana yakın davran, resmi dilden uzak dur."
            },
            "resmi": {
                "tone": "professional",
                "use_emoji": False,
                "verbose": True,
                "greeting": "İyi günler Efendim. F.R.I.D.A.Y. NEXUS asistanınız hizmete hazırdır.",
                "style_hint": "Son derece kibar, saygılı, resmi ve profesyonel bir dil kullanıyorsun. Kullanıcıya 'Efendim' diye hitap et."
            },
            "oyun": {
                "tone": "gamer",
                "use_emoji": True,
                "verbose": False,
                "greeting": "Sistemler hazır, ping stabil. GG WP! Hadi başlayalım. 🎮",
                "style_hint": "Hızlı, kısa, oyuncu terimleri (GG, WP, lag, FPS) içeren samimi bir dil kullan. Odak noktan performans ve oyun deneyimi olsun."
            }
        }
        self.current_mode = "arkadas"
        self.load_saved_mode()

    def set_mode(self, mode: str) -> str:
        if mode in self.PERSONALITY_MODES:
            self.current_mode = mode
            self._save_mode()
            return f"Kişilik modu '{mode}' olarak güncellendi. {self.PERSONALITY_MODES[mode]['greeting']}"
        return f"Geçersiz kişilik modu. Seçenekler: {list(self.PERSONALITY_MODES.keys())}"

    def get_prompt_prefix(self) -> str:
        mode_data = self.PERSONALITY_MODES.get(self.current_mode, self.PERSONALITY_MODES["arkadas"])
        return f"\n[KİŞİLİK & TON TALİMATI - ŞU ANKİ MOD: {self.current_mode.upper()}]\n{mode_data['style_hint']}\n"

    def detect_mode_from_text(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if "arkadaş modu" in text_lower or "arkadaşça konuş" in text_lower:
            return "arkadas"
        elif "teknik mod" in text_lower or "teknik konuş" in text_lower:
            return "teknik"
        elif "resmi mod" in text_lower or "resmi konuş" in text_lower:
            return "resmi"
        elif "oyun modu" in text_lower or "gamer mod" in text_lower:
            return "oyun"
        return None

    def _save_mode(self):
        try:
            from memory.memory_manager import update_memory
            update_memory({"settings": {"personality_mode": self.current_mode}})
        except Exception as e:
            logger.error(f"Error saving personality mode: {e}")

    def load_saved_mode(self):
        try:
            from memory.memory_manager import load_memory
            mem = load_memory()
            mode = mem.get("settings", {}).get("personality_mode")
            if mode in self.PERSONALITY_MODES:
                self.current_mode = mode
        except Exception:
            pass

personality_system = PersonalitySystem()
