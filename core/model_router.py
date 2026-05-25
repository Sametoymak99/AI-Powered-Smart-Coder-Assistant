import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ModelRouter")

class ModelRouter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelRouter, cls).__new__(cls)
            cls._instance._init_router()
        return cls._instance

    def _init_router(self):
        self.TASK_KEYWORDS = {
            "code": ["kod", "yaz", "debug", "python", "javascript", "script", "program", "gelistir", "class", "def "],
            "vision": ["goruntu", "ekran", "kamera", "foto", "resim", "analiz et", "ne var", "goster"],
            "planning": ["plan", "organize", "strateji", "yol haritasi", "adimlar", "ne yapmaliyim", "hedef"],
            "fast": ["hava", "saat", "tarih", "ses", "volume", "ac", "kapat", "dur", "cal"]
        }
        
        self.MODEL_MAP = {
            "code": {"ollama": "deepseek-coder", "gemini": "gemini-2.5-flash"},
            "vision": {"ollama": None, "gemini": "gemini-2.5-flash"},
            "planning": {"ollama": "qwen2.5", "gemini": "gemini-2.5-flash"},
            "fast": {"ollama": "gemma3", "gemini": "gemini-2.5-flash"},
            "default": {"ollama": "llama3.2", "gemini": "gemini-2.5-flash"}
        }

    def detect_task_type(self, text: str) -> str:
        text_lower = text.lower()
        for task_type, keywords in self.TASK_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return task_type
        return "default"

    def get_best_model(self, text: str, prefer_local: bool = False) -> Dict[str, Any]:
        task_type = self.detect_task_type(text)
        
        # Decide provider
        provider = "gemini"
        if prefer_local:
            # check if local model is available for task
            if self.MODEL_MAP[task_type]["ollama"] is not None:
                provider = "ollama"
                
        model_name = self.MODEL_MAP[task_type][provider]
        
        logger.info(f"Routed task '{task_type}' to {provider} using {model_name}")
        return {
            "provider": provider,
            "model": model_name,
            "task_type": task_type
        }

    def get_explanation(self, text: str) -> str:
        decision = self.get_best_model(text)
        return f"Bu görevi '{decision['task_type']}' kategorisinde algıladım. En uygun yanıt için '{decision['provider']}' üzerinden '{decision['model']}' modelini seçtim."

model_router = ModelRouter()
