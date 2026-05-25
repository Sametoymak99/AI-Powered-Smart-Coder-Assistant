import os
import requests
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("HomeAssistantPlugin")

TOOL_DECLARATIONS = [
    {
        "name": "ha_toggle_entity",
        "description": "Belirtilen Home Assistant entitesini (lamba, priz vb.) açar veya kapatır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "entity_id": {"type": "STRING", "description": "Örn: light.living_room, switch.smart_plug"}
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "ha_get_state",
        "description": "Belirtilen entitenin güncel durumunu (açık/kapalı, sıcaklık vb.) sorgular.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "entity_id": {"type": "STRING", "description": "Örn: sensor.living_room_temp"}
            },
            "required": ["entity_id"]
        }
    },
    {
        "name": "ha_call_service",
        "description": "Home Assistant üzerinde özel bir servis çağrısı gerçekleştirir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "domain": {"type": "STRING", "description": "Örn: climate, light"},
                "service": {"type": "STRING", "description": "Örn: set_temperature, turn_on"},
                "entity_id": {"type": "STRING", "description": "Hedef cihaz entity_id'si"},
                "data": {"type": "OBJECT", "description": "Ek servis verileri (JSON/Dictionary)"}
            },
            "required": ["domain", "service", "entity_id"]
        }
    }
]

def _get_headers() -> Dict[str, str]:
    # Try to load token from environment
    token = os.getenv("HA_TOKEN", "YOUR_HA_LONG_LIVED_ACCESS_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def _get_url() -> str:
    return os.getenv("HA_URL", "http://homeassistant.local:8123").rstrip("/")

def ha_toggle_entity(entity_id: str) -> str:
    url = f"{_get_url()}/api/services/homeassistant/toggle"
    data = {"entity_id": entity_id}
    try:
        res = requests.post(url, headers=_get_headers(), json=data, timeout=5)
        if res.status_code == 200:
            return f"Home Assistant entitesi {entity_id} durumu değiştirildi (Toggled)."
        return f"Hata: {res.status_code} - {res.text}"
    except Exception as e:
        logger.error(f"Home Assistant connection error: {e}")
        return f"Home Assistant bağlantı hatası: {e}"

def ha_get_state(entity_id: str) -> str:
    url = f"{_get_url()}/api/states/{entity_id}"
    try:
        res = requests.get(url, headers=_get_headers(), timeout=5)
        if res.status_code == 200:
            state_data = res.json()
            state = state_data.get("state", "Bilinmiyor")
            attributes = state_data.get("attributes", {})
            friendly_name = attributes.get("friendly_name", entity_id)
            return f"{friendly_name} durumu: {state}"
        return f"Hata: {res.status_code} - {res.text}"
    except Exception as e:
        logger.error(f"Home Assistant connection error: {e}")
        return f"Home Assistant bağlantı hatası: {e}"

def ha_call_service(domain: str, service: str, entity_id: str, data: Optional[Dict[str, Any]] = None) -> str:
    url = f"{_get_url()}/api/services/{domain}/{service}"
    payload = {"entity_id": entity_id}
    if data:
        payload.update(data)
    try:
        res = requests.post(url, headers=_get_headers(), json=payload, timeout=5)
        if res.status_code == 200:
            return f"{domain}.{service} servisi {entity_id} üzerinde çağrıldı."
        return f"Hata: {res.status_code} - {res.text}"
    except Exception as e:
        logger.error(f"Home Assistant connection error: {e}")
        return f"Home Assistant bağlantı hatası: {e}"

HANDLERS = {
    "ha_toggle_entity": ha_toggle_entity,
    "ha_get_state": ha_get_state,
    "ha_call_service": ha_call_service
}
