"""Read-only AVM Mesh WLAN radio observations for the device-detail model.

Never modifies the topology parser, links, aliases or device identities.
AVM rx_rcpi/tx_rcpi are retained as raw RCPI-like values, NOT dBm.
"""
from __future__ import annotations

from typing import Any, Mapping


# Strictly limited to non-identifying WLAN capability/measurement field names.
_RADIO_TOKENS = ("standard", "stream", "mimo", "max_data_rate",
                 "max_rate", "phy_mode", "wifi_mode", "wlan_mode",
                 "channel_width", "frequency_band", "bandwidth")


def _radio_fields(record: Mapping[str, Any]) -> dict[str, str | int | float | bool]:
    """Expose bounded raw radio metadata, without identifiers or nested payloads."""
    return {
        key: value for key, value in record.items()
        if isinstance(key, str) and len(key) <= 64
        and any(token in key.lower() for token in _RADIO_TOKENS)
        and isinstance(value, (str, int, float, bool))
        and (not isinstance(value, str) or len(value) <= 64)
    }


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
        if str(node.get("mesh_role", "")).lower() not in {"master", "slave"}:
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
                # Endpoint orientation is diagnostic only; do not relabel rates
                # as client download/upload without validated AVM semantics.
                values["mesh_rate_link_owner_is_node_1"] = node_uid == a
                values["mesh_rate_client_is_node_1"] = peer_uid == a
                values["mesh_rate_link_has_source_target"] = (
                    "source" in link and "target" in link
                )
                # Inspect the endpoint's own WLAN interface independently of
                # the AP/repeater radio. A peer interface is accepted only
                # when it explicitly references this very same Mesh link.
                # Never use the AP channel width as the client's width.
                if link_uid and isinstance(peer_interfaces, list):
                    for peer_interface in peer_interfaces:
                        if not isinstance(peer_interface, dict) or str(peer_interface.get("type", "")).upper() != "WLAN":
                            continue
                        peer_links = peer_interface.get("node_links", [])
                        if not isinstance(peer_links, list) or not any(
                            isinstance(candidate, dict)
                            and str(candidate.get("uid") or candidate.get("id") or "") == link_uid
                            for candidate in peer_links
                        ):
                            continue
                        peer_info = peer_interface.get("current_channel_info")
                        if isinstance(peer_info, dict) and peer_info.get("channel_width") is not None:
                            values["mesh_peer_interface_channel_width_raw"] = peer_info["channel_width"]
                        peer_channel = peer_interface.get("current_channel")
                        if isinstance(peer_channel, int) and peer_channel > 0:
                            values["mesh_peer_interface_channel"] = peer_channel
                        break
                for source, target in (
                    ("rx_rcpi", "mesh_rx_rcpi_raw"),
                    ("tx_rcpi", "mesh_tx_rcpi_raw"),
                    ("cur_data_rate_rx", "mesh_rate_rx_kbps"),
                    ("cur_data_rate_tx", "mesh_rate_tx_kbps"),
                ):
                    value = link.get(source)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        values[target] = value
                # Mesh rates are kbit/s. Keep raw fields and expose clearly
                # named Mbit/s values without changing topology or identities.
                for source, target in (
                    ("cur_data_rate_rx", "wifi_rate_rx_mbps"),
                    ("cur_data_rate_tx", "wifi_rate_tx_mbps"),
                    ("max_data_rate_rx", "wifi_rate_rx_max_mbps"),
                    ("max_data_rate_tx", "wifi_rate_tx_max_mbps"),
                ):
                    rate = link.get(source)
                    if isinstance(rate, (int, float)) and not isinstance(rate, bool) and rate >= 0:
                        values[target] = round(rate / 1000, 3)
                # Preserve the AVM mesh signal separately, with no unverified
                # assumption that RCPI values have a dBm unit.
                signal = link.get("rx_rcpi")
                if isinstance(signal, (int, float)) and not isinstance(signal, bool) and signal != 255:
                    values["wifi_mesh_signal_rx_raw"] = signal
                channel = interface.get("current_channel")
                if isinstance(channel, int) and channel > 0:
                    values["mesh_wifi_channel"] = channel
                info = interface.get("current_channel_info")
                if isinstance(info, dict) and info.get("channel_width") is not None:
                    values["mesh_wifi_channel_width_raw"] = info["channel_width"]
                # Preserve the exact source field names for a focused schema
                # check. No guessed Wi-Fi standard, stream count or max rate.
                for scope, record in (
                    ("link", link),
                    ("interface", interface),
                    ("channel", info if isinstance(info, dict) else {}),
                ):
                    raw_fields = _radio_fields(record)
                    if raw_fields:
                        values[f"mesh_wlan_{scope}_radio_fields"] = raw_fields
                if len(values) > 1:
                    result.setdefault(canonical, []).append(values)
    return result
