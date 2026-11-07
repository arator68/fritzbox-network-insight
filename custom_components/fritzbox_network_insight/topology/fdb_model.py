"""Conservative MAC-keyed switch forwarding observations, not direct links."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .lldp_matcher import normalize_mac

MAX_ENTRIES = 128


def build_fdb_observations(
    source_mac: str,
    entries: list[dict[str, Any]],
    hosts: Mapping[str, Mapping[str, Any]],
    *,
    observed_at: str | None = None,
) -> list[dict[str, str | None]]:
    """Correlate reachable MACs without claiming physical adjacency."""
    source = normalize_mac(source_mac)
    if source is None:
        return []
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    results: list[dict[str, str | None]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in entries[:MAX_ENTRIES]:
        if not isinstance(entry, dict):
            continue
        target = normalize_mac(entry.get("mac"))
        port = str(entry.get("bridge_port") or "")
        vlan = str(entry.get("vlan_id") or "")
        if not target or target == source or not port.isdecimal():
            continue
        if entry.get("connection") != "reachable_via_port":
            continue
        key = (vlan, port, target)
        if key in seen:
            continue
        seen.add(key)
        host = hosts.get(target, {})
        results.append({
            "source_mac": source,
            "target_mac": target,
            "target_name": str(host.get("name") or "")[:128] or None,
            "bridge_port": port,
            "vlan_id": vlan,
            "if_index": str(entry.get("if_index") or "")[:32],
            "interface_name": str(entry.get("interface_name") or "")[:128],
            "evidence": "fdb",
            "connection": "reachable_via_port",
            "observed_at": timestamp,
        })
    return results
