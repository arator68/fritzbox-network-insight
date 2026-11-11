"""Per-device connection view derived from the existing combined topology."""
from __future__ import annotations

from typing import Any, Mapping

from .device import normalize_mac


def connection_details(
    mac: str,
    host: Mapping[str, Any],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Project combined topology evidence onto one MAC without rescanning."""
    interface = str(host.get("interface_type") or "").strip().lower()
    kind = (
        "wlan" if interface in {"802.11", "wlan", "wifi", "wi-fi"}
        else "lan" if interface in {"ethernet", "lan"}
        else "unknown"
    )
    result: dict[str, Any] = {
        "connection_type": kind,
        "connected_to": None,
        "connected_to_mac": None,
        "connected_to_port": None,
        "connection_evidence": None,
        "connection_count": 0,
        "connections": [],
    }
    target = normalize_mac(mac)
    if target is None:
        return result

    names = {
        normalized: node.get("name") or normalized
        for node in snapshot.get("nodes", [])
        if isinstance(node, Mapping)
        if (normalized := normalize_mac(node.get("mac"))) is not None
    }
    direct: dict[tuple[str, str | None], dict[str, Any]] = {}
    for link in snapshot.get("direct_links", []):
        if not isinstance(link, Mapping) or link.get("connection") != "direct_confirmed":
            continue
        source = normalize_mac(link.get("source_mac"))
        remote = normalize_mac(link.get("target_mac"))
        if source is None or remote is None or source == remote:
            continue
        if target == source:
            peer = remote
            local_port = link.get("source_port_id")
            peer_port = link.get("target_port_id")
        elif target == remote:
            peer = source
            local_port = link.get("target_port_id")
            peer_port = link.get("source_port_id")
        else:
            continue
        local_port = str(local_port) if local_port else None
        direct[(peer, local_port)] = {
            "connected_to": names.get(peer, peer),
            "connected_to_mac": peer,
            "connected_to_port": local_port,
            "peer_port": str(peer_port) if peer_port else None,
            "evidence": "lldp_last_observed",
            "observed_at": link.get("observed_at"),
        }

    connections = sorted(
        direct.values(),
        key=lambda item: (item["connected_to_mac"], item["connected_to_port"] or ""),
    )
    result["connections"] = connections
    result["connection_count"] = len(connections)
    if connections:
        result["connection_evidence"] = (connections[0]["evidence"] if len(connections) == 1 else "multiple_confirmed_sources")
    if len(connections) == 1:
        only = connections[0]
        result.update({
            "connected_to": only["connected_to"],
            "connected_to_mac": only["connected_to_mac"],
            "connected_to_port": only["connected_to_port"],
        })

    # FDB only establishes reachability via a switch port, not direct wiring.
    reachable = []
    for link in snapshot.get("reachable_via_port", []):
        if not isinstance(link, Mapping) or link.get("connection") != "reachable_via_port":
            continue
        if normalize_mac(link.get("target_mac")) != target:
            continue
        switch_mac = normalize_mac(link.get("source_mac"))
        if switch_mac is None:
            continue
        reachable.append({
            "switch_mac": switch_mac,
            "interface_name": link.get("interface_name"),
            "evidence": "fdb_reachable_via_port",
        })
    if reachable:
        result["reachable_via_switch_ports"] = reachable

    # AVM reports its own topology; preserve the distinction from LLDP.
    mesh_links = []
    for link in snapshot.get("mesh_links", []):
        if not isinstance(link, Mapping):
            continue
        source = normalize_mac(link.get("source_mac"))
        remote = normalize_mac(link.get("target_mac"))
        if target == source and remote is not None:
            peer = remote
            local_port = link.get("source_interface")
            peer_port = link.get("target_interface")
        elif target == remote and source is not None:
            peer = source
            local_port = link.get("target_interface")
            peer_port = link.get("source_interface")
        else:
            continue
        mesh_links.append({
            "connected_to": names.get(peer, peer),
            "connected_to_mac": peer,
            "connected_to_port": local_port or None,
            "peer_port": peer_port or None,
            "link_type": link.get("link_type"),
            "link_state": link.get("link_state"),
            "evidence": "avm_mesh",
        })
    if mesh_links:
        result["mesh_reported_connections"] = mesh_links
    return result
