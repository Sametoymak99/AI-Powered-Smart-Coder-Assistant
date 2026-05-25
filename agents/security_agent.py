import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_bus import AgentBus

logger = logging.getLogger("SecurityAgent")

class SecurityAgent(BaseAgent):
    def __init__(self, bus: AgentBus):
        super().__init__("Security", bus)
        self.bus.subscribe("motion_detected", self.handle_event)
        self.bus.subscribe("face_scan_request", self.handle_event)
        self.bus.subscribe("alarm_trigger", self.handle_event)

    def handle_event(self, event: Dict[str, Any]):
        self.last_event = event
        etype = event.get("event_type")
        data = event.get("data", {})
        
        logger.info(f"SecurityAgent handling event {etype}")
        if etype == "motion_detected":
            self.trigger_alarm("Hareket Algılandı!")
        elif etype == "face_scan_request":
            self.check_face()
        elif etype == "alarm_trigger":
            self.trigger_alarm(data.get("reason", "Genel Alarm"))

    def check_face(self):
        logger.info("Face scan initiated...")
        try:
            from actions.camera_vision import capture_and_verify
            result = capture_and_verify()
            self.bus.publish("face_scan_result", {"verified": result}, self.name)
        except Exception as e:
            logger.error(f"Camera vision import/execution failed: {e}")
            self.bus.publish("face_scan_result", {"verified": False, "error": str(e)}, self.name)

    def trigger_alarm(self, reason: str):
        logger.warning(f"ALARM TRIGGERED: {reason}")
        self.bus.publish("alarm_status", {"active": True, "reason": reason}, self.name)
