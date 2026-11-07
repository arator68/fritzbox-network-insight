"""Persistent bounded storage for last manually observed LLDP links."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .lldp_matcher import normalize_mac

VERSION = 1
MAX_SOURCES = 32
MAX_LINKS_PER_SOURCE = 16
FIELDS = frozenset({
    "source_mac", "source_port_number", "source_port_id",
    "target_chassis_mac", "target_mac", "target_name", "target_port_id",
    "match_status", "evidence", "observed_at",
})


class TopologyStore:
    """Store LLDP observations without credentials or scan payloads."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(
            hass, VERSION, f"fritzbox_network_insight.topology.{entry_id}"
        )

    @staticmethod
    def sanitize(data: Any) -> dict[str, list[dict[str, Any]]]:
        if not isinstance(data, dict):
            return {}
        result: dict[str, list[dict[str, Any]]] = {}
        for source, links in list(data.items())[:MAX_SOURCES]:
            source_mac = normalize_mac(source)
            if not source_mac or not isinstance(links, list):
                continue
            safe: list[dict[str, Any]] = []
            for link in links[:MAX_LINKS_PER_SOURCE]:
                if not isinstance(link, dict):
                    continue
                if normalize_mac(link.get("source_mac")) != source_mac:
                    continue
                if not normalize_mac(link.get("target_chassis_mac")):
                    continue
                cleaned = {
                    key: value[:256]
                    for key, value in link.items()
                    if key in FIELDS and isinstance(value, str)
                }
                if cleaned.get("evidence") != "lldp":
                    continue
                safe.append(cleaned)
            result[source_mac] = safe
        return result

    async def async_load(self) -> dict[str, list[dict[str, Any]]]:
        data = await self._store.async_load()
        return self.sanitize(data.get("observations")) if isinstance(data, dict) else {}

    async def async_save(self, observations: dict[str, list[dict[str, Any]]]) -> None:
        await self._store.async_save({
            "observations": self.sanitize(observations)
        })
