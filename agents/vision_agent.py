import logging
import time
import threading
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from .agent_bus import AgentBus

logger = logging.getLogger("VisionAgent")

class VisionAgent(BaseAgent):
    def __init__(self, bus: AgentBus):
        super().__init__("Vision", bus)
        self.bus.subscribe("screen_analyze", self.handle_event)
        self.bus.subscribe("ocr_request", self.handle_event)
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    def handle_event(self, event: Dict[str, Any]):
        self.last_event = event
        etype = event.get("event_type")
        data = event.get("data", {})
        
        logger.info(f"VisionAgent handling event {etype}")
        if etype == "screen_analyze":
            self.analyze_screen()
        elif etype == "ocr_request":
            self.run_ocr(data.get("image_path"))

    def setup(self):
        self.start_monitoring()

    def cleanup(self):
        self.stop_monitoring()

    def start_monitoring(self, interval: int = 5):
        if self._monitoring:
            return
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        self._monitoring = False

    def _monitor_loop(self, interval: int):
        while self._monitoring:
            try:
                # Real-time app check
                from core.screen_monitor import screen_monitor
                context = screen_monitor.analyze_context()
                self.bus.publish("screen_context_change", context, self.name)
            except Exception as e:
                logger.error(f"Error in vision monitor loop: {e}")
            time.sleep(interval)

    def analyze_screen(self):
        try:
            from actions.screen_vision import capture_screen
            img = capture_screen()
            self.bus.publish("screen_capture_success", {"image": "captured"}, self.name)
        except Exception as e:
            logger.error(f"Screen analyze failed: {e}")
            self.bus.publish("screen_capture_failed", {"error": str(e)}, self.name)

    def run_ocr(self, image_path: Optional[str]):
        try:
            from actions.screen_vision import do_ocr
            res = do_ocr(image_path)
            self.bus.publish("ocr_result", {"text": res}, self.name)
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            self.bus.publish("ocr_result", {"error": str(e)}, self.name)
