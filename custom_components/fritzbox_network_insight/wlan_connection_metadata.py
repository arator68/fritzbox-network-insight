"""Read-only WLAN connection metadata for device sensors.

Only explicit association observations are displayed. The reported Mesh peer
is not an independently verified physical topology connection.
"""
from __future__ import annotations

from typing import Any, Mapping

from .device import normalize_mac
from .device_details import DeviceDetails


def connection_metadata(
    mac: str, host: Mapping[str, Any] | None, details: DeviceDetails | None,
    hosts: Mapping[str, Mapping[str, Any]], mesh_topology: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    if not host or not details or not host.get("active"):
        return {}
    if str(host.get("interface_type") or "").strip().lower() not in {
        "802.11", "wlan", "wifi", "wi-fi"
    }:
        return {}

    result: dict[str, dict[str, Any]] = {
        "role": {"value": "WLAN-Client", "source": "host_interface_type"}
    }

    # Explicit frequency-band observation only; never infer from channel or
    # the WLANConfiguration service instance.
    for observation in details.values("wifi_frequency_band_mhz"):
        if observation.value in (2400, 5000, 6000):
            result["band"] = {
                "value": {2400: "2,4 GHz", 5000: "5 GHz", 6000: "6 GHz"}[observation.value],
                "source": observation.source,
                "observed_at": observation.observed_at,
            }
            break

    # Require exactly one connected WLAN Mesh peer for this MAC. This is
    # reported association metadata, not a change to the topology graph.
    peers: set[str] = set()
    for observation in details.values("mesh_reported_link"):
        link = observation.value
        if not isinstance(link, dict):
            continue
        if str(link.get("link_type") or "").upper() != "WLAN":
            continue
        if str(link.get("link_state") or "").upper() != "CONNECTED":
            continue
        peer = normalize_mac(link.get("peer_mac"))
        if peer and peer != mac:
            peers.add(peer)
    if len(peers) == 1:
        peer = next(iter(peers))
        aliases = mesh_topology.get("aliases") or {}
        canonical = aliases.get(peer, peer)
        nodes = mesh_topology.get("nodes") or []
        node = next((n for n in nodes if isinstance(n, dict) and n.get("mac") == canonical), None)
        name = (hosts.get(canonical) or {}).get("dns_name") or (hosts.get(canonical) or {}).get("name")
        if not name and node:
            name = node.get("name")
        if isinstance(name, str) and name.strip():
            result["peer"] = {
                "value": name.strip(), "source": "avm_mesh",
                "peer_mac": peer, "connection_scope": "avm_reported_wlan_link",
            }
    return result
