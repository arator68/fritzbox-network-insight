"""Persistent MAC-based switch-port history, never a source of confirmed cables."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .lldp_matcher import normalize_mac

VERSION = 1
MAX_RECORDS = 2048


def sanitize_history(value: Any) -> list[dict[str, str]]:
    """Validate stored observations and deduplicate by switch, MAC and VLAN."""
    if not isinstance(value, list):
        return []
    records: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in value[:MAX_RECORDS]:
        if not isinstance(item, dict):
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if not source or not target or source == target:
            continue
        port = str(item.get("bridge_port") or "").strip()
        vlan = str(item.get("vlan_id") or "").strip()
        name = str(item.get("interface_name") or "").strip()
        seen = str(item.get("last_seen") or "").strip()
        evidence = str(item.get("evidence") or "")
        if (not port or len(port) > 32 or len(vlan) > 32 or
                len(name) > 128 or evidence not in ("fdb_reachability", "lldp") or
                len(seen) > 40):
            continue
        try:
            datetime.fromisoformat(seen.replace("Z", "+00:00"))
        except ValueError:
            continue
        records[(source, target, vlan)] = {
            "source_mac": source, "target_mac": target,
            "bridge_port": port, "vlan_id": vlan,
            "interface_name": name, "evidence": evidence,
            "last_seen": seen,
        }
    return sorted(records.values(), key=lambda v: (
        v["source_mac"], v["target_mac"], v["vlan_id"]
    ))


def merge_port_history(
    history: list[dict[str, str]],
    observations: list[Mapping[str, Any]],
    *,
    observed_at: str | None = None,
) -> list[dict[str, str]]:
    """Update a successful scan; retain devices absent from later scans."""
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    by_key = {
        (v["source_mac"], v["target_mac"], v["vlan_id"]): dict(v)
        for v in sanitize_history(history)
    }
    for item in observations:
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        port = str(item.get("bridge_port") or "").strip()
        vlan = str(item.get("vlan_id") or "").strip()
        if not source or not target or source == target or not port:
            continue
        key = (source, target, vlan)
        by_key[key] = {
            "source_mac": source, "target_mac": target,
            "bridge_port": port, "vlan_id": vlan,
            "interface_name": str(item.get("interface_name") or "")[:128],
            "evidence": "fdb_reachability",
            "last_seen": timestamp,
        }
    return sanitize_history(list(by_key.values())[-MAX_RECORDS:])


class PortHistoryStore:
    """Home Assistant store scoped to one integration entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store(
            hass, VERSION, f"fritzbox_network_insight.port_history.{entry_id}"
        )

    async def async_load(self) -> list[dict[str, str]]:
        data = await self._store.async_load()
        return sanitize_history(data.get("records")) if isinstance(data, dict) else []

    async def async_save(self, records: list[dict[str, str]]) -> None:
        await self._store.async_save({"records": sanitize_history(records)})
