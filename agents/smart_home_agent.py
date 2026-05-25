import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_bus import AgentBus

logger = logging.getLogger("SmartHomeAgent")

class SmartHomeAgent(BaseAgent):
    def __init__(self, bus: AgentBus):
        super().__init__("SmartHome", bus)
        self.bus.subscribe("arduino_command", self.handle_event)
        self.bus.subscribe("iot_command", self.handle_event)

    def handle_event(self, event: Dict[str, Any]):
        self.last_event = event
        etype = event.get("event_type")
        data = event.get("data", {})
        
        logger.info(f"SmartHomeAgent handling event {etype}")
        if etype == "arduino_command":
            self.send_arduino(data.get("cmd", ""))
        elif etype == "iot_command":
            self.send_iot(data)

    def send_arduino(self, command: str):
        try:
            from actions.arduino_control import send_command
            res = send_command(command)
            self.bus.publish("arduino_result", {"success": True, "result": res}, self.name)
        except Exception as e:
            logger.error(f"Arduino send failed: {e}")
            self.bus.publish("arduino_result", {"success": False, "error": str(e)}, self.name)

    def send_iot(self, data: Dict[str, Any]):
        # Custom ESP32/MQTT or JSON endpoints
        logger.info(f"Sending IoT command: {data}")
        # Placeholder/simulated for now, can publish to local MQTT bus
        self.bus.publish("iot_result", {"success": True, "command": data}, self.name)
