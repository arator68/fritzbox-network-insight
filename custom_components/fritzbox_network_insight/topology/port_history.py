"""Persistent MAC-based switch-port history; observations never prove direct cables."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .lldp_matcher import normalize_mac

VERSION = 1
MAX_RECORDS = 2048


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def sanitize_history(value: Any) -> list[dict[str, str]]:
    """Validate and retain the newest observation per switch, MAC and VLAN."""
    if not isinstance(value, list):
        return []
    records: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        if not source or not target or source == target:
            continue
        port = str(item.get("bridge_port") or "").strip()
        vlan = str(item.get("vlan_id") or "").strip()
        name = str(item.get("interface_name") or "").strip()
        seen = _timestamp(item.get("last_seen"))
        evidence = str(item.get("evidence") or "")
        if (not port or len(port) > 32 or len(vlan) > 32
                or len(name) > 128
                or evidence not in ("fdb_reachability", "lldp")
                or seen is None):
            continue
        key = (source, target, vlan)
        normalized = {
            "source_mac": source, "target_mac": target,
            "bridge_port": port, "vlan_id": vlan,
            "interface_name": name, "evidence": evidence,
            "last_seen": seen.isoformat(),
        }
        previous = records.get(key)
        if previous is None or seen > _timestamp(previous["last_seen"]):
            records[key] = normalized
    # Limit by most recent observation, not by MAC sort order.
    newest = sorted(records.values(), key=lambda record: (
        record["last_seen"], record["source_mac"], record["target_mac"],
        record["vlan_id"]
    ), reverse=True)[:MAX_RECORDS]
    return sorted(newest, key=lambda record: (
        record["source_mac"], record["target_mac"], record["vlan_id"]
    ))


def merge_port_history(
    history: list[dict[str, str]],
    observations: list[Mapping[str, Any]],
    *,
    observed_at: str | None = None,
) -> list[dict[str, str]]:
    """Merge one complete successful FDB scan, retaining absent MACs."""
    seen_at = _timestamp(observed_at) if observed_at is not None else datetime.now(timezone.utc)
    if seen_at is None:
        raise ValueError("observed_at must contain a timezone-aware ISO timestamp")
    timestamp = seen_at.isoformat()
    by_key = {
        (v["source_mac"], v["target_mac"], v["vlan_id"]): dict(v)
        for v in sanitize_history(history)
    }
    for item in observations:
        source = normalize_mac(item.get("source_mac"))
        target = normalize_mac(item.get("target_mac"))
        port = str(item.get("bridge_port") or "").strip()
        vlan = str(item.get("vlan_id") or "").strip()
        name = str(item.get("interface_name") or "").strip()
        if (not source or not target or source == target or not port
                or len(port) > 32 or len(vlan) > 32 or len(name) > 128):
            continue
        key = (source, target, vlan)
        previous = by_key.get(key)
        if previous is not None and _timestamp(previous["last_seen"]) > seen_at:
            continue  # Never let an older scan replace a newer port.
        by_key[key] = {
            "source_mac": source, "target_mac": target,
            "bridge_port": port, "vlan_id": vlan,
            "interface_name": name,
            "evidence": "fdb_reachability",
            "last_seen": timestamp,
        }
    return sanitize_history(list(by_key.values()))


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
