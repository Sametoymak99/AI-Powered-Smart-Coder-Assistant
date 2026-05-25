import logging
import asyncio
from typing import Dict, Any
from .base_agent import BaseAgent
from .agent_bus import AgentBus

logger = logging.getLogger("CodingAgent")

class CodingAgent(BaseAgent):
    def __init__(self, bus: AgentBus):
        super().__init__("Coding", bus)
        self.bus.subscribe("code_request", self.handle_event)
        self.bus.subscribe("debug_request", self.handle_event)

    def handle_event(self, event: Dict[str, Any]):
        self.last_event = event
        etype = event.get("event_type")
        data = event.get("data", {})
        
        logger.info(f"CodingAgent handling event {etype}")
        if etype == "code_request":
            self.generate_code(data.get("task", ""), data.get("filename", "generated_code.py"))
        elif etype == "debug_request":
            self.run_tests(data.get("project_dir", "."))

    def generate_code(self, task: str, filename: str):
        logger.info(f"Generating code for task: {task}")
        try:
            from autonomous_coder import run_autonomous_coder
            # run_autonomous_coder is async or sync. Let's call it safely
            async def run_task():
                res = await run_autonomous_coder(task)
                self.bus.publish("code_result", {"success": True, "result": res}, self.name)
            
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(run_task(), loop)
                else:
                    loop.run_until_complete(run_task())
            except Exception:
                asyncio.run(run_task())
                
        except Exception as e:
            logger.error(f"Coding agent run failed: {e}")
            self.bus.publish("code_result", {"success": False, "error": str(e)}, self.name)

    def run_tests(self, project_dir: str):
        logger.info(f"Running tests in {project_dir}")
        # Run pytest inside venv or locally
        import subprocess
        try:
            res = subprocess.run(["pytest", project_dir], capture_output=True, text=True, timeout=30)
            self.bus.publish("test_result", {"success": res.returncode == 0, "output": res.stdout + res.stderr}, self.name)
        except Exception as e:
            self.bus.publish("test_result", {"success": False, "error": str(e)}, self.name)
