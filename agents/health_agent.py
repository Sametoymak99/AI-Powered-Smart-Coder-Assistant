import logging
import json
from pathlib import Path
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_bus import AgentBus

logger = logging.getLogger("HealthAgent")

BASE_DIR = Path(__file__).resolve().parent.parent
HEALTH_FILE = BASE_DIR / "memory" / "health_data.json"

class HealthAgent(BaseAgent):
    def __init__(self, bus: AgentBus):
        super().__init__("Health", bus)
        self.bus.subscribe("health_query", self.handle_event)
        self.bus.subscribe("health_update", self.handle_event)

    def handle_event(self, event: Dict[str, Any]):
        self.last_event = event
        etype = event.get("event_type")
        data = event.get("data", {})
        
        logger.info(f"HealthAgent handling event {etype}")
        if etype == "health_query":
            summary = self.get_summary()
            self.bus.publish("health_summary", summary, self.name)
        elif etype == "health_update":
            self.update_health(data)

    def get_summary(self) -> Dict[str, Any]:
        try:
            if HEALTH_FILE.exists():
                with open(HEALTH_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error reading health file: {e}")
        return {"status": "Veri yok", "calories": 0, "steps": 0, "sleep": 0}

    def update_health(self, data: Dict[str, Any]):
        current = self.get_summary()
        current.update(data)
        try:
            with open(HEALTH_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2, ensure_ascii=False)
            self.bus.publish("health_status_updated", current, self.name)
        except Exception as e:
            logger.error(f"Error writing health file: {e}")
            self.bus.publish("health_status_updated", {"error": str(e)}, self.name)
