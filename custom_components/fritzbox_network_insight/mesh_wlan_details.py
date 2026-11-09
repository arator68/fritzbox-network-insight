"""Read-only AVM Mesh WLAN radio observations for the device-detail model.

Never modifies the topology parser, links, aliases or device identities.
AVM rx_rcpi/tx_rcpi are retained as raw RCPI-like values, NOT dBm.
"""
from __future__ import annotations

from typing import Any, Mapping

from .device import normalize_mac


def extract_mesh_wlan_details(
    payload: Mapping[str, Any], aliases: Mapping[str, str]
) -> dict[str, list[dict[str, Any]]]:
    """Extract per-endpoint radio measurements from explicit Mesh node links.

    Only WLAN interfaces and links marked CONNECTED are considered. Endpoint
    attribution uses the owner of the interface and the node UID; no hostnames
    or topology inference. Results are separate observations, not graph edges.
    """
    nodes = payload.get("nodes", [])
    if not isinstance(nodes, list):
        return {}
    by_uid: dict[str, dict] = {}
    for node in nodes:
        if isinstance(node, dict) and node.get("uid") is not None:
            by_uid[str(node["uid"])] = node
    result: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for node_uid, node in by_uid.items():
        interfaces = node.get("node_interfaces", [])
        if not isinstance(interfaces, list):
            continue
        for interface in interfaces:
            if not isinstance(interface, dict) or str(interface.get("type", "")).upper() != "WLAN":
                continue
            links = interface.get("node_links", [])
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, dict) or str(link.get("state", "")).upper() != "CONNECTED":
                    continue
                a, b = str(link.get("node_1_uid") or ""), str(link.get("node_2_uid") or "")
                if node_uid not in (a, b):
                    continue
                peer_uid = b if a == node_uid else a
                peer = by_uid.get(peer_uid)
                if peer is None:
                    continue
                peer_macs = [peer.get("device_mac_address"), peer.get("device_mac"), peer.get("mac_address")]
                peer_interfaces = peer.get("node_interfaces", [])
                if isinstance(peer_interfaces, list):
                    peer_macs.extend(i.get("mac_address") for i in peer_interfaces if isinstance(i, dict))
                canonical = next(
                    (aliases.get(mac, mac) for value in peer_macs
                     if (mac := normalize_mac(value)) and mac in aliases),
                    None,
                )
                if canonical is None:
                    continue
                link_uid = str(link.get("uid") or link.get("id") or "")
                signature = (canonical, link_uid, node_uid)
                if signature in seen:
                    continue
                seen.add(signature)
                values: dict[str, Any] = {"peer_node_uid": node_uid}
                for source, target in (
                    ("rx_rcpi", "mesh_rx_rcpi_raw"),
                    ("tx_rcpi", "mesh_tx_rcpi_raw"),
                    ("cur_data_rate_rx", "mesh_rate_rx_kbps"),
                    ("cur_data_rate_tx", "mesh_rate_tx_kbps"),
                ):
                    value = link.get(source)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        values[target] = value
                channel = interface.get("current_channel")
                if isinstance(channel, int) and channel > 0:
                    values["mesh_wifi_channel"] = channel
                info = interface.get("current_channel_info")
                if isinstance(info, dict) and info.get("channel_width") is not None:
                    values["mesh_wifi_channel_width_raw"] = info["channel_width"]
                if len(values) > 1:
                    result.setdefault(canonical, []).append(values)
    return result
