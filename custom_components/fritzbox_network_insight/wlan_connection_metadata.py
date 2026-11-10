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

    # Prefer an explicit band observation. Channel fallback is allowed only
    # for the endpoint-associated Mesh peer interface or client WLAN channel.
    for observation in details.values("wifi_frequency_band_mhz"):
        if observation.value in (2400, 5000, 6000):
            result["band"] = {
                "value": {2400: "2,4 GHz", 5000: "5 GHz", 6000: "6 GHz"}[observation.value],
                "source": observation.source,
                "observed_at": observation.observed_at,
            }
            break

    if "band" not in result:
        # Do not infer 6 GHz from a bare channel number: 6 GHz channel
        # numbering overlaps with 2.4 and 5 GHz.
        # Only unambiguous, established 5-GHz channel numbers are used.
        five_ghz_channels = {
            36, 40, 44, 48, 52, 56, 60, 64,
            100, 104, 108, 112, 116, 120, 124, 128,
            132, 136, 140, 144, 149, 153, 157, 161,
            165, 169, 173, 177,
        }
        for field in ("mesh_peer_interface_channel", "mesh_wifi_channel", "wifi_channel"):
            for observation in details.values(field):
                try:
                    channel = int(observation.value)
                except (TypeError, ValueError):
                    continue
                if channel in five_ghz_channels:
                    result["band"] = {
                        "value": "5 GHz",
                        "source": "derived_from_wlan_channel",
                        "source_field": field,
                        "source_observation": observation.source,
                        "channel": channel,
                        "observed_at": observation.observed_at,
                    }
                    break
            if "band" in result:
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
