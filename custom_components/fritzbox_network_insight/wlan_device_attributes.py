"""Build source-aware WLAN attributes without guessing missing measurements."""
from __future__ import annotations

from typing import Any

from .device_details import DeviceDetails


# Explicitly supported observations. Mesh RCPI-like values remain raw.
_WLAN_KEYS = (
    "wifi_rate_rx_mbps", "wifi_rate_tx_mbps",
    "wifi_rate_rx_max_mbps", "wifi_rate_tx_max_mbps",
    "wifi_speed_mbps", "wifi_speed_rx_mbps",
    "wifi_speed_max_mbps", "wifi_speed_rx_max_mbps",
    "wifi_channel", "mesh_wifi_channel",
    "mesh_peer_interface_channel", "mesh_peer_interface_channel_width_raw",
    "wifi_channel_width", "mesh_wifi_channel_width_raw",
    "wifi_frequency_band_mhz", "wifi_guest",
    "wifi_signal_strength", "wifi_mesh_signal_rx_raw",
    "mesh_rx_rcpi_raw", "mesh_tx_rcpi_raw",
    "mesh_rate_rx_kbps", "mesh_rate_tx_kbps",
    "peer_node_uid",
    "mesh_rate_link_owner_is_node_1",
    "mesh_rate_client_is_node_1",
    "mesh_rate_link_has_source_target",
    "mesh_connected_ap_interface_mac",
    "mesh_connected_ap_interface_ref_matches_link",
    "mesh_connected_ap_interface_type",
    "mesh_connected_ap_band_mhz",
    "mesh_connected_ap_primary_freq_mhz",
    "repeater_tr064_wifi_speed_mbps",
    "repeater_tr064_wifi_speed_rx_mbps",
    "repeater_tr064_wifi_speed_max_mbps",
    "repeater_tr064_wifi_speed_rx_max_mbps",
    "repeater_tr064_associated_speed_mbps",
    "repeater_tr064_wifi_signal_strength",
    "repeater_tr064_wifi_channel",
    "repeater_tr064_wifi_channel_width",
)

# Mesh radio metadata is recorded as raw source-specific dictionaries. Only
# explicitly named, scalar fields are surfaced; no band/standard inference.
_MESH_RADIO_FIELDS = {
    "mesh_wlan_link_radio_fields": ("wifi_standard", "stream_count", "phy_mode", "wifi_mode", "wlan_mode"),
    "mesh_wlan_interface_radio_fields": ("wifi_standard", "stream_count", "phy_mode", "wifi_mode", "wlan_mode"),
    "mesh_wlan_channel_radio_fields": ("channel_width", "frequency_band"),
    "mesh_wlan_connected_ap_interface_radio_fields": ("channel_width", "frequency_band"),
    "mesh_wlan_connected_ap_channel_radio_fields": ("channel_width", "frequency_band"),
}



def wlan_details_attribute(details: DeviceDetails | None, interface_type: Any) -> list[dict[str, Any]]:
    """Return only recorded WLAN facts, preserving competing sources and timestamps.

    A channel reported by TR-064 is not substituted for a Mesh channel.
    Zero is a valid recorded value. No signal unit or access-point name is inferred.
    """
    if details is None or str(interface_type or "").strip().lower() not in {
        "802.11", "wlan", "wifi", "wi-fi",
    }:
        return []

    observations: list[dict[str, Any]] = []
    for key in _WLAN_KEYS:
        for observation in details.values(key):
            value = observation.value
            if not isinstance(value, (str, int, float, bool)):
                continue
            row = {
                "field": key,
                "value": value,
                "source": observation.source,
                "observed_at": observation.observed_at,
            }
            if key == "wifi_channel_width":
                # TR-064 WLAN device list: not interchangeable with Mesh radio width.
                row["measurement_scope"] = "tr064_wlan_device"
            elif key == "mesh_wifi_channel_width_raw":
                row["measurement_scope"] = "mesh_radio_channel"
            observations.append(row)
    # Only publish radio metadata that AVM actually supplied for this endpoint.
    # Keep raw field names, provenance and timestamp; do not synthesize Wi-Fi 4,
    # 2.4 GHz, 20 MHz or stream counts from other measurements.
    for key, allowed_fields in _MESH_RADIO_FIELDS.items():
        for observation in details.values(key):
            raw = observation.value
            if not isinstance(raw, dict):
                continue
            for field in allowed_fields:
                value = raw.get(field)
                if not isinstance(value, (str, int, float, bool)):
                    continue
                if isinstance(value, str) and (not value.strip() or len(value) > 64):
                    continue
                scope = key.removeprefix("mesh_wlan_").removesuffix("_radio_fields")
                observations.append({
                    "field": "mesh_radio_channel_width" if field == "channel_width" and scope == "channel" else field,
                    "value": value,
                    "source": observation.source,
                    "observed_at": observation.observed_at,
                    "raw_scope": scope,
                    **({"measurement_scope": "mesh_radio_channel"} if field == "channel_width" and scope == "channel" else {}),
                })
    # Schema diagnostics already filtered by mesh_wlan_details. Revalidate
    # type labels and whitelist the only value-bearing radio fields.
    for key in ("mesh_wlan_connected_ap_interface_schema", "mesh_wlan_connected_ap_channel_schema"):
        for observation in details.values(key):
            if not isinstance(observation.value, dict):
                continue
            safe = {}
            for field, entry in observation.value.items():
                if not isinstance(field, str) or not isinstance(entry, dict):
                    continue
                kind = entry.get("type")
                if kind not in ("object", "array", "boolean", "number", "string", "null", "other"):
                    continue
                item = {"type": kind}
                value = entry.get("value")
                if field in ("current_channel", "frequency", "frequency_mhz", "frequency_band", "channel_width", "bandwidth") and isinstance(value, (int, float)) and not isinstance(value, bool):
                    item["value"] = value
                elif field in ("channel_width", "bandwidth") and isinstance(value, str) and len(value) <= 16 and all(c.isdigit() or c in " .MHzmhz" for c in value):
                    item["value"] = value
                safe[field] = item
            if safe:
                observations.append({"field": key, "value": safe, "source": observation.source, "observed_at": observation.observed_at})
    # Mesh peer is a reported MAC, not necessarily a confirmed physical AP.
    for observation in details.values("mesh_reported_link"):
        link = observation.value
        if not isinstance(link, dict) or str(link.get("link_type", "")).upper() != "WLAN":
            continue
        peer = link.get("peer_mac")
        if isinstance(peer, str) and peer:
            observations.append({
                "field": "mesh_reported_wlan_peer_mac",
                "value": peer,
                "source": observation.source,
                "observed_at": observation.observed_at,
            })
    return observations
