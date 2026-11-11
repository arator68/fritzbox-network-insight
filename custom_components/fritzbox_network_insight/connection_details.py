"""Conservative, source-labelled connection metadata for device status attributes."""
from __future__ import annotations

from typing import Any, Mapping

from .device import normalize_mac


def connection_details(
    mac: str,
    host: Mapping[str, Any],
    hosts: Mapping[str, Mapping[str, Any]],
    topology: Mapping[str, list[dict[str, Any]]],
    fdb: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Distinguish a verified LLDP neighbor from FDB reachability."""
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
    # LLDP is an observed adjacency, not proof that the link is still live.
    # For each endpoint, expose its own local port rather than the peer's port.
    matches: dict[tuple[str, str | None], dict[str, Any]] = {}
    for source_mac, links in topology.items():
        source = normalize_mac(source_mac)
        for link in links:
            if not isinstance(link, Mapping) or link.get("match_status") != "matched":
                continue
            remote = normalize_mac(link.get("target_mac"))
            if source is None or remote is None or source == remote:
                continue
            if target == source:
                peer = remote
                local_port = str(link.get("source_port_id") or "") or None
                peer_port = str(link.get("target_port_id") or "") or None
            elif target == remote:
                peer = source
                local_port = str(link.get("target_port_id") or "") or None
                peer_port = str(link.get("source_port_id") or "") or None
            else:
                continue
            peer_host = hosts.get(peer, {})
            matches[(peer, local_port)] = {
                "connected_to": peer_host.get("name") or peer,
                "connected_to_mac": peer,
                "connected_to_port": local_port,
                "peer_port": peer_port,
                "evidence": "lldp_last_observed",
                "observed_at": link.get("observed_at"),
            }
    connections = sorted(
        matches.values(),
        key=lambda item: (item["connected_to_mac"], item["connected_to_port"] or ""),
    )
    result["connections"] = connections
    result["connection_count"] = len(connections)
    if connections:
        result["connection_evidence"] = "lldp_last_observed"
    if len(connections) == 1:
        only = connections[0]
        result.update({
            "connected_to": only["connected_to"],
            "connected_to_mac": only["connected_to_mac"],
            "connected_to_port": only["connected_to_port"],
        })
    # FDB is reachability evidence, never proof of direct cabling.
    reachable = []
    for switch_mac, observations in fdb.items():
        for observation in observations:
            if (
                isinstance(observation, Mapping)
                and normalize_mac(observation.get("target_mac")) == target
                and observation.get("connection") == "reachable_via_port"
            ):
                reachable.append({
                    "switch_mac": normalize_mac(switch_mac),
                    "interface_name": observation.get("interface_name"),
                    "evidence": "fdb_reachable_via_port",
                })
    if reachable:
        result["reachable_via_switch_ports"] = reachable
    return result
