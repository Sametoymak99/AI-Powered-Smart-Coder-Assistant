import abc
import threading
from typing import Dict, Any
from .agent_bus import AgentBus

class BaseAgent(abc.ABC):
    def __init__(self, name: str, bus: AgentBus):
        self.name = name
        self.bus = bus
        self.running = False
        self.last_event: Dict[str, Any] = {}
        self._thread = None
        self.bus.register_agent(self.name, self)

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, name=f"Agent-{self.name}", daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def _run_loop(self):
        self.setup()
        while self.running:
            self.loop_step()
        self.cleanup()

    def setup(self):
        pass

    def loop_step(self):
        import time
        time.sleep(0.5)

    def cleanup(self):
        pass

    @abc.abstractmethod
    def handle_event(self, event: Dict[str, Any]):
        pass

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "running": self.running,
            "last_event": self.last_event
        }
