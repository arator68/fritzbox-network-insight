"""Evidence-preserving per-device topology resolution.

A forwarding-table port is a route through a switch, not a physical cable.
The resolver never turns FDB observations or history into physical edges.
"""
from __future__ import annotations

from typing import Any, Mapping


def resolve_device_connections(graph: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build one deterministic connection summary per known MAC."""
    nodes = graph.get("nodes") or {}
    result: dict[str, dict[str, Any]] = {}

    def record(mac: str) -> dict[str, Any]:
        if mac not in result:
            node = nodes.get(mac, {}) if isinstance(nodes, dict) else {}
            result[mac] = {
                "mac": mac,
                "name": str(node.get("name") or ""),
                "ip_address": str(node.get("ip_address") or ""),
                "connection_type": "unknown",
                "parent_mac": None,
                "switch_mac": None,
                "bridge_port": None,
                "vlan_id": None,
                "interface_name": None,
                "evidence": None,
                "physical_link_confirmed": False,
                "last_seen": None,
                "status": "unknown",
            }
        return result[mac]

    # Historical FDB observations are useful only as last-known routing.
    for item in graph.get("port_history", []):
        mac = item.get("target_mac")
        if not mac:
            continue
        entry = record(mac)
        entry.update({
            "connection_type": "last_known_port",
            "switch_mac": item.get("source_mac"),
            "bridge_port": item.get("bridge_port"),
            "vlan_id": item.get("vlan_id"),
            "interface_name": item.get("interface_name"),
            "evidence": "fdb_history",
            "last_seen": item.get("last_seen"),
            "status": "historical",
        })

    # Current FDB reachability supersedes history, but is not a cable.
    for group in graph.get("lan_port_memberships", []):
        for member in group.get("members", []):
            mac = member.get("mac")
            if not mac:
                continue
            entry = record(mac)
            entry.update({
                "connection_type": "reachable_via_port",
                "switch_mac": group.get("switch_mac"),
                "bridge_port": group.get("bridge_port"),
                "vlan_id": group.get("vlan_id"),
                "interface_name": (group.get("interface_names") or [None])[0],
                "evidence": "fdb_reachability",
                "status": "observed_in_saved_fdb",
            })

    # A WLAN parent is more specific than the wired path carrying its traffic.
    for mac, attachment in sorted(graph.get("wlan_attachments", {}).items()):
        entry = record(mac)
        entry.update({
            "connection_type": "wlan",
            "parent_mac": attachment.get("parent_mac"),
            "evidence": "avm_mesh",
            "status": "mesh_observed",
        })

    # Only LLDP and explicit user confirmation can assert a direct cable.
    # Never mistake AVM logical LAN evidence for a physical link.
    for link in graph.get("links", []):
        if link.get("medium") != "lan" or link.get("evidence") not in (
            "lldp", "user_confirmed"
        ):
            continue
        source = link.get("source_mac")
        target = link.get("target_mac")
        if not source or not target:
            continue
        entry = record(target)
        entry.update({
            "connection_type": "confirmed_lan",
            "parent_mac": source,
            "evidence": link["evidence"],
            "physical_link_confirmed": True,
            "status": "confirmed",
        })
    return [result[mac] for mac in sorted(result)]
