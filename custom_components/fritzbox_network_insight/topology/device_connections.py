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
                "transit_neighbor_mac": None,
                "transit_evidence": None,
                "port_relationship": None,
                "wlan_parent_connection": None,
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

    # Confirmed neighbor on a port can identify the downstream transit path,
    # but cannot establish a direct cable to other MACs learned there.
    confirmed_by_port = {}
    for group in graph.get("lan_port_memberships", []):
        key = (group.get("switch_mac"), group.get("bridge_port"), group.get("vlan_id"))
        confirmed_by_port[key] = {
            member["mac"] for member in group.get("members", [])
            if member.get("physical_link_confirmed") and member.get("mac")
        }

    # Current FDB reachability supersedes history, but is not a cable.
    for group in graph.get("lan_port_memberships", []):
        for member in group.get("members", []):
            mac = member.get("mac")
            if not mac:
                continue
            entry = record(mac)
            key = (group.get("switch_mac"), group.get("bridge_port"), group.get("vlan_id"))
            neighbors = confirmed_by_port.get(key, set()) - {mac}
            transit = next(iter(neighbors)) if len(neighbors) == 1 else None
            entry.update({
                "connection_type": "reachable_via_port",
                "switch_mac": group.get("switch_mac"),
                "bridge_port": group.get("bridge_port"),
                "vlan_id": group.get("vlan_id"),
                "interface_name": (group.get("interface_names") or [None])[0],
                "evidence": "fdb_reachability",
                "status": "observed_in_saved_fdb",
                "port_relationship": member.get("relationship"),
                "transit_neighbor_mac": transit,
                "transit_evidence": "confirmed_port_neighbor" if transit else None,
            })

    # A WLAN parent is more specific than the wired path carrying its traffic.
    for mac, attachment in sorted(graph.get("wlan_attachments", {}).items()):
        entry = record(mac)
        entry.update({
            "connection_type": "wlan",
            "parent_mac": attachment.get("parent_mac"),
            "evidence": "avm_mesh",
            "status": "mesh_observed",
            "wlan_parent_connection": "unverified",
        })

    # Only LLDP can assert a direct cable.
    # Never mistake AVM logical LAN evidence for a physical link.
    for link in graph.get("links", []):
        if link.get("medium") != "lan" or link.get("evidence") != "lldp":
            continue
        source = link.get("source_mac")
        target = link.get("target_mac")
        if not source or not target:
            continue
        entry = record(target)
        if link.get("state") == "needs_review":
            # A disputed LLDP observation is not an active physical link.
            entry.update({
                "connection_type": "disputed_lan",
                "parent_mac": None,
                "evidence": "lldp",
                "physical_link_confirmed": False,
                "status": "needs_review",
            })
            continue
        entry.update({
            "connection_type": "confirmed_lan",
            "parent_mac": source,
            "evidence": link["evidence"],
            "physical_link_confirmed": True,
            "status": "confirmed",
        })
    # A repeater learned via FDB may use Ethernet or wireless backhaul.
    # Preserve that uncertainty rather than inventing a cable.
    for entry in result.values():
        if entry["connection_type"] != "wlan":
            continue
        parent = result.get(entry["parent_mac"])
        if parent and parent["connection_type"] == "confirmed_lan":
            entry["wlan_parent_connection"] = "confirmed_lan"
        elif parent and parent["connection_type"] == "reachable_via_port":
            entry["wlan_parent_connection"] = "fdb_reachable_only"
    return [result[mac] for mac in sorted(result)]
