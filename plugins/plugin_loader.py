import os
import json
import logging
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Callable

logger = logging.getLogger("PluginLoader")

class PluginLoader:
    def __init__(self, plugins_dir: str = None):
        if plugins_dir is None:
            self.plugins_dir = Path(__file__).resolve().parent
        else:
            self.plugins_dir = Path(plugins_dir)
        
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.tool_declarations: List[Dict[str, Any]] = []
        self.handlers: Dict[str, Callable] = {}

    def scan_and_load(self):
        self.plugins.clear()
        self.tool_declarations.clear()
        self.handlers.clear()
        
        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory does not exist: {self.plugins_dir}")
            return

        for entry in os.scandir(self.plugins_dir):
            if entry.is_dir():
                manifest_path = Path(entry.path) / "manifest.json"
                if manifest_path.exists():
                    try:
                        self.load_plugin(entry.path, manifest_path)
                    except Exception as e:
                        logger.error(f"Error loading plugin from {entry.path}: {e}")

    def load_plugin(self, plugin_dir: str, manifest_path: Path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        
        name = manifest.get("name")
        enabled = manifest.get("enabled", True)
        if not name:
            return
            
        manifest["path"] = plugin_dir
        self.plugins[name] = manifest
        
        if not enabled:
            logger.info(f"Plugin {name} is disabled.")
            return

        entry_file = manifest.get("entry", "plugin.py")
        entry_path = Path(plugin_dir) / entry_file
        
        if not entry_path.exists():
            logger.error(f"Plugin entry file not found: {entry_path}")
            return

        # Dynamically import module
        module_name = f"plugins.{name.lower().replace(' ', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, str(entry_path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Load tools
            if hasattr(module, "TOOL_DECLARATIONS"):
                self.tool_declarations.extend(module.TOOL_DECLARATIONS)
            if hasattr(module, "HANDLERS"):
                self.handlers.update(module.HANDLERS)
                
            logger.info(f"Loaded plugin: {name}")

    def get_tool_declarations(self) -> List[Dict[str, Any]]:
        return self.tool_declarations

    def get_all_handlers(self) -> Dict[str, Callable]:
        return self.handlers

    def enable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name]["enabled"] = True
            self._save_manifest(name)
            self.scan_and_load()
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        if name in self.plugins:
            self.plugins[name]["enabled"] = False
            self._save_manifest(name)
            self.scan_and_load()
            return True
        return False

    def _save_manifest(self, name: str):
        plugin_info = self.plugins[name]
        manifest_path = Path(plugin_info["path"]) / "manifest.json"
        
        # Save back, omit helper 'path' key
        save_data = {k: v for k, v in plugin_info.items() if k != "path"}
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Could not save manifest for {name}: {e}")

    def list_plugins(self) -> List[Dict[str, Any]]:
        return list(self.plugins.values())

plugin_loader = PluginLoader()
