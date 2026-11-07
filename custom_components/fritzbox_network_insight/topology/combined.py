"""Combined topology evidence; LLDP links and FDB reachability stay distinct."""
from __future__ import annotations

from typing import Any, Mapping

from .lldp_matcher import normalize_mac


def build_combined_topology(
    lldp: Mapping[str, list[dict[str, Any]]],
    fdb: Mapping[str, list[dict[str, Any]]],
    hosts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Merge MAC identities, never promote FDB evidence to a physical link."""
    nodes: dict[str, dict[str, Any]] = {}
    for raw_mac, host in hosts.items():
        mac = normalize_mac(raw_mac)
        if mac:
            nodes[mac] = {
                "mac": mac, "name": str(host.get("name") or ""),
                "ip_address": str(host.get("ip_address") or ""),
                "device_type": host.get("device_type"),
                "known_host": True,
            }

    def ensure_node(mac: str) -> None:
        if mac not in nodes:
            nodes[mac] = {
                "mac": mac, "name": "", "ip_address": "",
                "device_type": None, "known_host": False,
            }

    direct: list[dict[str, Any]] = []
    reachable: list[dict[str, Any]] = []
    seen_direct: set[tuple[str, str, str]] = set()
    seen_reachable: set[tuple[str, str, str, str]] = set()
    for source, links in sorted(lldp.items()):
        source_mac = normalize_mac(source)
        if not source_mac:
            continue
        for link in links:
            if not isinstance(link, dict) or link.get("match_status") != "matched":
                continue
            target = normalize_mac(link.get("target_mac"))
            if not target or target == source_mac:
                continue
            port = str(link.get("source_port_number") or "")
            key = (source_mac, port, target)
            if key in seen_direct:
                continue
            seen_direct.add(key)
            ensure_node(source_mac)
            ensure_node(target)
            direct.append({
                "source_mac": source_mac, "target_mac": target,
                "source_port_number": port,
                "source_port_id": link.get("source_port_id"),
                "target_port_id": link.get("target_port_id"),
                "evidence": "lldp", "connection": "direct_confirmed",
                "observed_at": link.get("observed_at"),
            })
    for source, entries in sorted(fdb.items()):
        source_mac = normalize_mac(source)
        if not source_mac:
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("connection") != "reachable_via_port":
                continue
            target = normalize_mac(entry.get("target_mac"))
            if not target or target == source_mac:
                continue
            port = str(entry.get("bridge_port") or "")
            vlan = str(entry.get("vlan_id") or "")
            key = (source_mac, vlan, port, target)
            if key in seen_reachable:
                continue
            seen_reachable.add(key)
            ensure_node(source_mac)
            ensure_node(target)
            reachable.append({
                "source_mac": source_mac, "target_mac": target,
                "bridge_port": port, "vlan_id": vlan,
                "interface_name": entry.get("interface_name"),
                "evidence": "fdb", "connection": "reachable_via_port",
                "observed_at": entry.get("observed_at"),
            })
    return {
        "nodes": [nodes[mac] for mac in sorted(nodes)],
        "direct_links": direct,
        "reachable_via_port": reachable,
        "node_count": len(nodes),
        "direct_link_count": len(direct),
        "reachability_count": len(reachable),
        "lldp_source_count": len(lldp),
        "fdb_source_count": len(fdb),
        "evidence": "last_manual_observations",
    }
