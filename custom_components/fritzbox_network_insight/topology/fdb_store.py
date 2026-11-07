"""Bounded persistent last-manual FDB observations, separate from LLDP links."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .lldp_matcher import normalize_mac

MAX_SOURCES = 16
MAX_ENTRIES = 128
FIELDS = {
    "source_mac", "target_mac", "target_name", "bridge_port", "vlan_id",
    "if_index", "interface_name", "evidence", "connection", "observed_at",
}


class FdbTopologyStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(hass, 1, f"fritzbox_network_insight.fdb.{entry_id}")

    @staticmethod
    def sanitize(data: Any) -> dict[str, list[dict[str, str | None]]]:
        if not isinstance(data, dict):
            return {}
        output: dict[str, list[dict[str, str | None]]] = {}
        for source, entries in list(data.items())[:MAX_SOURCES]:
            mac = normalize_mac(source)
            if not mac or not isinstance(entries, list):
                continue
            safe = []
            for entry in entries[:MAX_ENTRIES]:
                if not isinstance(entry, dict):
                    continue
                if (normalize_mac(entry.get("source_mac")) != mac
                        or not normalize_mac(entry.get("target_mac"))
                        or entry.get("connection") != "reachable_via_port"
                        or entry.get("evidence") != "fdb"):
                    continue
                safe.append({
                    key: value[:256] if isinstance(value, str) else None
                    for key, value in entry.items()
                    if key in FIELDS and (isinstance(value, str) or value is None)
                })
            output[mac] = safe
        return output

    async def async_load(self) -> dict[str, list[dict[str, str | None]]]:
        data = await self._store.async_load()
        return self.sanitize(data.get("observations")) if isinstance(data, dict) else {}

    async def async_save(self, observations: dict[str, list[dict[str, str | None]]]) -> None:
        await self._store.async_save({"observations": self.sanitize(observations)})
