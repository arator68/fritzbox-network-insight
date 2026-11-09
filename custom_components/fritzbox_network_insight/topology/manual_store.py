"""Persist explicit user-confirmed physical LAN connections per config entry."""
from __future__ import annotations

from typing import Any
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from .lldp_matcher import normalize_mac

VERSION = 1
MAX_LINKS = 128


def sanitize_links(value: Any) -> list[dict[str, str]]:
    """Reject malformed records; never turn observations into confirmations."""
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in value[:MAX_LINKS]:
        if not isinstance(item, dict) or item.get("confirmation") != "user_confirmed":
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if not source or not target or source == target:
            continue
        pair = tuple(sorted((source, target)))
        if pair in seen:
            continue
        seen.add(pair)
        port = str(item.get("bridge_port") or "").strip()
        vlan = str(item.get("vlan_id") or "").strip()
        if len(port) > 32 or len(vlan) > 32:
            continue
        result.append({
            "source_mac": source, "target_mac": target,
            "bridge_port": port, "vlan_id": vlan,
            "confirmation": "user_confirmed",
        })
    return result


class ManualTopologyStore:
    """Home Assistant storage for manually confirmed links."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(
            hass, VERSION, f"fritzbox_network_insight.manual_links.{entry_id}"
        )

    async def async_load(self) -> list[dict[str, str]]:
        data = await self._store.async_load()
        return sanitize_links(data.get("links")) if isinstance(data, dict) else []

    async def async_save(self, links: list[dict[str, str]]) -> None:
        await self._store.async_save({"links": sanitize_links(links)})
