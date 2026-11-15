"""Read-only WLAN connection metadata for device sensors.

Only explicit association observations are displayed. The reported Mesh peer
is not an independently verified physical topology connection.
"""
from __future__ import annotations

from typing import Any, Mapping

from .device import normalize_mac
from .device_details import DeviceDetails


def _display_role(
    mac: str, host: Mapping[str, Any], mesh_topology: Mapping[str, Any],
) -> tuple[str, str]:
    """Use explicit device classification or AVM Mesh role, never the hostname."""
    kind = str(host.get("device_type") or "").strip().lower()
    labels = {
        "router": "Router", "switch": "Switch", "repeater": "Repeater",
        "access_point": "Access Point", "access point": "Access Point",
    }
    if kind:
        return labels.get(kind, "Endgerät"), "device_type"

    # AVM Mesh identifies infrastructure nodes independently of the host
    # interface type. Only a matching MAC and explicit Mesh role count.
    aliases = mesh_topology.get("aliases") or {}
    canonical = aliases.get(normalize_mac(mac), normalize_mac(mac))
    for node in mesh_topology.get("nodes") or []:
        if not isinstance(node, dict) or normalize_mac(node.get("mac")) != canonical:
            continue
        role = str(node.get("mesh_role") or "").strip().lower()
        if role in {"repeater", "mesh_repeater", "mesh repeater"}:
            return "Repeater", "avm_mesh_role"
        break

    # Successful TR-064 WLANConfiguration responses from the device itself
    # establish an infrastructure WLAN access point, not an ordinary client.
    raw = host.get("repeater_raw_data")
    if isinstance(raw, dict) and raw.get("available") is True and raw.get("wlan_services"):
        return "Repeater", "repeater_tr064"
    return "Endgerät", "device_type"


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

    role, role_source = _display_role(mac, host, mesh_topology)
    result: dict[str, dict[str, Any]] = {
        "role": {"value": role, "source": role_source}
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
        # The Mesh extractor associates this AP/repeater radio interface with
        # the specific CONNECTED client link, rather than the router globally.
        for observation in details.values("mesh_connected_ap_band_mhz"):
            if observation.value in (2400, 5000, 6000):
                result["band"] = {
                    "value": {2400: "2,4 GHz", 5000: "5 GHz", 6000: "6 GHz"}[observation.value],
                    "source": "avm_mesh_connected_ap_interface",
                    "source_observation": observation.source,
                    "observed_at": observation.observed_at,
                }
                break

    if "band" not in result:
        # Channels 1-14 overlap 2.4 GHz and 6 GHz: never derive a band
        # from those channel numbers without an explicit band observation.
        # The listed 5 GHz primary channels do not overlap 6 GHz primary
        # channel numbering. Do not infer from other channel numbers.
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
                band = "5 GHz" if channel in five_ghz_channels else None
                if band:
                    result["band"] = {
                        "value": band,
                        "source": "derived_from_wlan_channel",
                        "source_field": field,
                        "source_observation": observation.source,
                        "channel": channel,
                        "inferred": True,
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
