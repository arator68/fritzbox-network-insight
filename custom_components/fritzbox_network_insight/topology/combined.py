"""Combined topology evidence; LLDP links and FDB reachability stay distinct."""
from __future__ import annotations

from typing import Any, Mapping

from .lldp_matcher import normalize_mac


def build_combined_topology(
    lldp: Mapping[str, list[dict[str, Any]]],
    fdb: Mapping[str, list[dict[str, Any]]],
    hosts: Mapping[str, Mapping[str, Any]],
    mesh: Mapping[str, Any] | None = None,
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
    mesh = mesh or {}
    mesh_links: list[dict[str, Any]] = []
    seen_mesh: set[tuple[str, str, str]] = set()
    for node in mesh.get("nodes", []):
        if not isinstance(node, dict):
            continue
        mac = normalize_mac(node.get("mac"))
        if not mac:
            continue
        ensure_node(mac)
        if not nodes[mac]["name"] and node.get("name"):
            nodes[mac]["name"] = str(node["name"])
        nodes[mac]["mesh_role"] = node.get("mesh_role")
        # Only a Mesh master is unambiguously a router. A Mesh slave
        # can be a repeater or a second FRITZ!Box; both act as an
        # access point, but the role alone cannot distinguish models.
        # Never overwrite an existing manually/protocol-classified type.
        role = str(node.get("mesh_role") or "").strip().lower()
        if not nodes[mac].get("device_type") and role in ("master", "slave"):
            nodes[mac]["device_type"] = (
                "router" if role == "master" else "access_point"
            )
            nodes[mac]["device_type_source"] = "avm_mesh_role"
            nodes[mac]["device_type_confidence"] = "detected"
    for link in mesh.get("links", []):
        if not isinstance(link, dict):
            continue
        source = normalize_mac(link.get("source_mac"))
        target = normalize_mac(link.get("target_mac"))
        if not source or not target or source == target:
            continue
        key = tuple(sorted((source, target))) + (str(link.get("link_type") or ""),)
        if key in seen_mesh:
            continue
        seen_mesh.add(key)
        ensure_node(source)
        ensure_node(target)
        mesh_links.append(dict(link))
    return {
        "nodes": [nodes[mac] for mac in sorted(nodes)],
        "direct_links": direct,
        "mesh_links": mesh_links,
        "reachable_via_port": reachable,
        "node_count": len(nodes),
        "direct_link_count": len(direct),
        "mesh_link_count": len(mesh_links),
        "mesh_node_count": len(mesh.get("nodes", [])),
        "mesh_unresolved_link_count": mesh.get("unresolved_link_count", 0),
        "reachability_count": len(reachable),
        "lldp_source_count": len(lldp),
        "fdb_source_count": len(fdb),
        "evidence": "last_manual_observations",
    }
