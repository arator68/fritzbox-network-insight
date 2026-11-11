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
    }
    target = normalize_mac(mac)
    if target is None:
        return result
    matches: list[tuple[str, str | None]] = []
    for source_mac, links in topology.items():
        source = normalize_mac(source_mac)
        for link in links:
            if not isinstance(link, Mapping) or link.get("match_status") != "matched":
                continue
            remote = normalize_mac(link.get("target_mac"))
            if target == remote and source is not None:
                matches.append((source, str(link.get("source_port_id") or "") or None))
            elif target == source and remote is not None:
                matches.append((remote, str(link.get("target_port_id") or "") or None))
    distinct = set(matches)
    if len(distinct) == 1:
        peer, port = next(iter(distinct))
        peer_host = hosts.get(peer, {})
        result.update({
            "connected_to": peer_host.get("name") or peer,
            "connected_to_mac": peer,
            "connected_to_port": port,
            "connection_evidence": "lldp_last_observed",
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
