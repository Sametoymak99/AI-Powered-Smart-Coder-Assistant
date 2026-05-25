import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_bus import AgentBus

logger = logging.getLogger("PersonalAgent")

class PersonalAgent(BaseAgent):
    def __init__(self, bus: AgentBus):
        super().__init__("Personal", bus)
        self.bus.subscribe("email_request", self.handle_event)
        self.bus.subscribe("whatsapp_request", self.handle_event)
        self.bus.subscribe("reminder_request", self.handle_event)
        self.bus.subscribe("calendar_request", self.handle_event)

    def handle_event(self, event: Dict[str, Any]):
        self.last_event = event
        etype = event.get("event_type")
        data = event.get("data", {})
        
        logger.info(f"PersonalAgent handling event {etype}")
        if etype == "email_request":
            self.send_email(data)
        elif etype == "whatsapp_request":
            self.send_whatsapp(data)
        elif etype == "reminder_request":
            self.set_reminder(data)
        elif etype == "calendar_request":
            self.manage_calendar(data)

    def send_email(self, data: Dict[str, Any]):
        try:
            from actions.email_manager import send_email_action
            res = send_email_action(data.get("to"), data.get("subject"), data.get("body"))
            self.bus.publish("email_result", {"success": True, "result": res}, self.name)
        except Exception as e:
            logger.error(f"Email failed: {e}")
            self.bus.publish("email_result", {"success": False, "error": str(e)}, self.name)

    def send_whatsapp(self, data: Dict[str, Any]):
        try:
            from actions.whatsapp import send_message
            res = send_message(data.get("contact"), data.get("message"))
            self.bus.publish("whatsapp_result", {"success": True, "result": res}, self.name)
        except Exception as e:
            logger.error(f"WhatsApp failed: {e}")
            self.bus.publish("whatsapp_result", {"success": False, "error": str(e)}, self.name)

    def set_reminder(self, data: Dict[str, Any]):
        try:
            from actions.reminders import add_reminder
            res = add_reminder(data.get("text"), data.get("time"))
            self.bus.publish("reminder_result", {"success": True, "result": res}, self.name)
        except Exception as e:
            logger.error(f"Reminder failed: {e}")
            self.bus.publish("reminder_result", {"success": False, "error": str(e)}, self.name)

    def manage_calendar(self, data: Dict[str, Any]):
        try:
            from actions.calendar import add_event
            res = add_event(data.get("title"), data.get("start"), data.get("end"))
            self.bus.publish("calendar_result", {"success": True, "result": res}, self.name)
        except Exception as e:
            logger.error(f"Calendar failed: {e}")
            self.bus.publish("calendar_result", {"success": False, "error": str(e)}, self.name)
