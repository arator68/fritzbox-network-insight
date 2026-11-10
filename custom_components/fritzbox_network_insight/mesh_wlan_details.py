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


def _safe_interface_schema(record: Mapping[str, Any]) -> dict[str, Any]:
    """Expose field names and types, not arbitrary values or nested content.

    Only numeric channel/frequency values and bounded channel-width strings
    are shown. Unknown fields reveal their key and type only. This keeps
    credentials, addresses and device identifiers out of HA attributes.
    """
    result: dict[str, Any] = {}
    for key, value in record.items():
        if not isinstance(key, str) or len(key) > 64:
            continue
        lower = key.lower()
        if any(token in lower for token in (
            "pass", "secret", "token", "auth", "credential", "key",
            "mac", "ip", "address", "name", "ssid", "uid", "serial",
        )):
            continue
        if isinstance(value, dict):
            kind = "object"
        elif isinstance(value, list):
            kind = "array"
        elif isinstance(value, bool):
            kind = "boolean"
        elif isinstance(value, (int, float)):
            kind = "number"
        elif isinstance(value, str):
            kind = "string"
        elif value is None:
            kind = "null"
        else:
            kind = "other"
        item: dict[str, Any] = {"type": kind}
        if lower in {"current_channel", "frequency", "frequency_mhz", "frequency_band"}:
            if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 100000:
                item["value"] = value
        elif lower in {"channel_width", "bandwidth"}:
            if isinstance(value, str) and len(value) <= 16 and all(
                char.isdigit() or char in " .MHzmhz" for char in value
            ):
                item["value"] = value
            elif isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 10000:
                item["value"] = value
        result[key] = item
        if len(result) >= 40:
            break
    return result


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
                # Diagnostic interface identity: exact MAC of the WLAN radio
                # that owns this CONNECTED link, not the repeater device MAC.
                # Compare against link interface references when available.
                radio_mac = normalize_mac(interface.get("mac_address"))
                if radio_mac:
                    values["mesh_connected_ap_interface_mac"] = radio_mac
                interface_uid = str(interface.get("uid") or interface.get("id") or "")
                link_interface_refs = {
                    str(link.get(key))
                    for key in ("node_interface_1_uid", "node_interface_2_uid")
                    if link.get(key) is not None
                }
                if link_interface_refs:
                    values["mesh_connected_ap_interface_ref_matches_link"] = (
                        interface_uid in link_interface_refs
                    )
                values["mesh_connected_ap_interface_type"] = "WLAN"
                # Frequency belongs to this exact connected AP radio, not to
                # the repeater uplink or another WLAN interface.
                # AVM may report MHz, kHz or Hz; reject unknown units.
                if isinstance(info, dict):
                    frequency = info.get("primary_freq")
                    if isinstance(frequency, (int, float)) and not isinstance(frequency, bool):
                        mhz = (
                            frequency if 2000 <= frequency <= 8000 else
                            frequency / 1000 if 2000000 <= frequency <= 8000000 else
                            frequency / 1000000 if 2000000000 <= frequency <= 8000000000 else
                            None
                        )
                        if mhz is not None:
                            band = (
                                2400 if 2400 <= mhz < 2500 else
                                5000 if 4900 <= mhz < 5925 else
                                6000 if 5925 <= mhz <= 7125 else
                                None
                            )
                            if band is not None:
                                values["mesh_connected_ap_primary_freq_mhz"] = round(mhz, 3)
                                values["mesh_connected_ap_band_mhz"] = band
                # Band belongs to the AP interface owning this connected client link.
                # Never borrow another interface's band or infer from channel.
                info = interface.get("current_channel_info")
                for record in (info if isinstance(info, dict) else {}, interface):
                    raw_band = record.get("frequency_band")
                    if raw_band in (2400, 5000, 6000):
                        values["mesh_connected_ap_band_mhz"] = raw_band
                        break
                    if isinstance(raw_band, str):
                        normalized = {
                            "2.4ghz": 2400, "2,4ghz": 2400,
                            "5ghz": 5000, "6ghz": 6000,
                        }.get(raw_band.strip().lower().replace(" ", ""))
                        if normalized is not None:
                            values["mesh_connected_ap_band_mhz"] = normalized
                            break
                # Bounded, read-only diagnostics from the exact AP/repeater
                # interface owning this connected client link. Do not expose
                # MACs, UIDs, names, addresses or arbitrary nested payloads.
                # Empty diagnostics are omitted. These observations are not
                # used for topology construction or band inference.
                for scope, record in (
                    ("connected_ap_interface", interface),
                    ("connected_ap_channel", info if isinstance(info, dict) else {}),
                ):
                    diagnostic = _radio_fields(record)
                    if diagnostic:
                        values[f"mesh_wlan_{scope}_radio_fields"] = diagnostic
                # Schema-only diagnostics of the exact connected AP interface.
                # Unknown values are deliberately withheld for privacy.
                for scope, record in (
                    ("connected_ap_interface_schema", interface),
                    ("connected_ap_channel_schema", info if isinstance(info, dict) else {}),
                ):
                    schema = _safe_interface_schema(record)
                    if schema:
                        values[f"mesh_wlan_{scope}"] = schema
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
