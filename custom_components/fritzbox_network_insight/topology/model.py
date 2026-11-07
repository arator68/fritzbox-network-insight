"""MAC-keyed topology observations built only from verified LLDP advertisements."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .lldp_matcher import normalize_mac


def build_lldp_links(
    source_mac: str,
    neighbors: list[dict[str, Any]],
    *,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Turn actual LLDP observations into explicit, provenance-tagged links."""
    source = normalize_mac(source_mac)
    if source is None:
        return []
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for neighbor in neighbors:
        if not isinstance(neighbor, dict):
            continue
        local_port = str(neighbor.get("local_port_id") or "")
        local_number = str(neighbor.get("local_port_number") or "")
        if not local_number.isdecimal():
            continue
        chassis = (
            normalize_mac(neighbor.get("chassis_id"))
            if str(neighbor.get("chassis_id_subtype")) == "4"
            else None
        )
        if chassis is None:
            continue
        matched = normalize_mac(neighbor.get("matched_mac"))
        status = str(neighbor.get("match_status") or "unmatched")
        verified = status == "matched" and matched == chassis
        remote_port = str(neighbor.get("port_id") or "")
        identity = (local_number, chassis, remote_port)
        if identity in seen:
            continue
        seen.add(identity)
        links.append({
            "source_mac": source,
            "source_port_number": local_number,
            "source_port_id": local_port[:128],
            "target_chassis_mac": chassis,
            "target_mac": matched if verified else None,
            "target_name": str(neighbor.get("matched_name") or "")[:128] if verified else None,
            "target_port_id": remote_port[:128],
            "match_status": "matched" if verified else (
                "ambiguous" if status == "ambiguous" else "unmatched"
            ),
            "evidence": "lldp",
            "observed_at": timestamp,
        })
    return links


def topology_snapshot(
    observations: Mapping[str, list[dict[str, Any]]],
    hosts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return known nodes and last-observed edges; do not claim current links."""
    nodes = [{
        "mac": mac,
        "name": str(host.get("name") or ""),
        "ip_address": str(host.get("ip_address") or ""),
        "device_type": host.get("device_type"),
    } for mac, host in sorted(hosts.items())]
    links = [
        dict(link)
        for source in sorted(observations)
        for link in observations[source]
    ]
    return {
        "nodes": nodes,
        "links": links,
        "link_count": len(links),
        "matched_link_count": sum(link.get("match_status") == "matched" for link in links),
        "evidence": "last_manual_lldp_observation",
    }
