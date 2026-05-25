import threading
import logging
from typing import Callable, Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentBus")

class AgentBus:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgentBus, cls).__new__(cls)
                cls._instance._init_bus()
            return cls._instance

    def _init_bus(self):
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.events_log: List[Dict[str, Any]] = []
        self.max_log_size = 200
        self.agents: Dict[str, Any] = {}
        self.log_lock = threading.Lock()

    def register_agent(self, agent_name: str, agent_instance: Any):
        with self._lock:
            self.agents[agent_name] = agent_instance
            logger.info(f"Agent registered: {agent_name}")

    def get_agent_status(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            status = {}
            for name, inst in self.agents.items():
                if hasattr(inst, "status"):
                    status[name] = inst.status
                else:
                    status[name] = {"running": False, "last_event": None}
            return status

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        with self._lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            self.subscribers[event_type].append(callback)
            logger.info(f"Subscribed callback to event: {event_type}")

    def publish(self, event_type: str, data: Dict[str, Any], source: str):
        event = {
            "event_type": event_type,
            "data": data,
            "source": source,
            "timestamp": threading.current_thread().name
        }
        
        with self.log_lock:
            self.events_log.append(event)
            if len(self.events_log) > self.max_log_size:
                self.events_log.pop(0)

        logger.info(f"Event published: {event_type} from {source}")

        # Get subscribers
        callbacks = []
        with self._lock:
            if event_type in self.subscribers:
                callbacks = list(self.subscribers[event_type])
            if "*" in self.subscribers:
                callbacks.extend(self.subscribers["*"])

        for cb in callbacks:
            try:
                threading.Thread(target=cb, args=(event,), daemon=True).start()
            except Exception as e:
                logger.error(f"Error executing callback for event {event_type}: {e}")

agent_bus = AgentBus()
