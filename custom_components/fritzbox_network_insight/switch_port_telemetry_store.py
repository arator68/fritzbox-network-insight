"""Persist bounded last-observed SNMP switch port telemetry for startup recovery.

These are historical measurements, not proof of current link state or wiring.
"""
from __future__ import annotations

import json
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .device import normalize_mac

MAX_SWITCHES = 16
MAX_PORTS = 128


class SwitchPortTelemetryStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, 1, f"fritzbox_network_insight.switch_ports.{entry_id}")

    @staticmethod
    def sanitize(data: Any) -> dict[str, dict[str, str]]:
        if not isinstance(data, dict):
            return {}
        output: dict[str, dict[str, str]] = {}
        for raw_mac, observation in list(data.items())[:MAX_SWITCHES]:
            mac = normalize_mac(raw_mac)
            if mac is None or not isinstance(observation, dict):
                continue
            try:
                ports = json.loads(observation.get("port_telemetry", ""))
            except (TypeError, ValueError):
                continue
            if not isinstance(ports, list) or len(ports) > MAX_PORTS:
                continue
            safe_ports: list[dict[str, Any]] = []
            for port in ports:
                if not isinstance(port, dict):
                    break
                index = port.get("if_index")
                name = port.get("interface_name")
                if not isinstance(index, int) or isinstance(index, bool) or not isinstance(name, str):
                    break
                safe: dict[str, Any] = {"if_index": index, "interface_name": name[:128]}
                speed = port.get("reported_speed_mbps")
                if isinstance(speed, (int, float)) and not isinstance(speed, bool) and 0 <= speed <= 1000000:
                    safe["reported_speed_mbps"] = speed
                for key in ("speed_source", "oper_status"):
                    value = port.get(key)
                    if isinstance(value, str):
                        safe[key] = value[:64]
                safe_ports.append(safe)
            else:
                if observation.get("port_telemetry_status") == "ok":
                    output[mac] = {
                        "port_telemetry_status": "ok",
                        "port_telemetry": json.dumps(safe_ports),
                        "last_run": str(observation.get("last_run") or "")[:64],
                    }
        return output

    async def async_load(self) -> dict[str, dict[str, str]]:
        data = await self._store.async_load()
        return self.sanitize(data)

    async def async_save(self, observations: dict[str, dict[str, str]]) -> None:
        await self._store.async_save(self.sanitize(observations))
