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
    "wifi_channel_width", "mesh_wifi_channel_width_raw",
    "wifi_frequency_band_mhz", "wifi_guest",
    "wifi_signal_strength", "wifi_mesh_signal_rx_raw",
    "mesh_rx_rcpi_raw", "mesh_tx_rcpi_raw",
    "peer_node_uid",
)

# Mesh radio metadata is recorded as raw source-specific dictionaries. Only
# explicitly named, scalar fields are surfaced; no band/standard inference.
_MESH_RADIO_FIELDS = {
    "mesh_wlan_link_radio_fields": ("wifi_standard", "stream_count", "phy_mode", "wifi_mode", "wlan_mode"),
    "mesh_wlan_interface_radio_fields": ("wifi_standard", "stream_count", "phy_mode", "wifi_mode", "wlan_mode"),
    "mesh_wlan_channel_radio_fields": ("channel_width", "frequency_band"),
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


# Compact presentation data for dashboards. Raw observations remain in
# wlan_details and are never replaced by this view.
_PRESENTATION_FIELDS = (
    ("wifi_channel", "WLAN-Kanal (TR-064)", None),
    ("mesh_wifi_channel", "Mesh-Kanal", None),
    ("wifi_channel_width", "WLAN-Gerät – Kanalbreite (TR-064)", "MHz"),
    ("mesh_radio_channel_width", "Mesh-Funkkanal – Kanalbreite", None),
    ("wifi_rate_rx_mbps", "Empfangsdatenrate (Mesh)", "Mbit/s"),
    ("wifi_rate_tx_mbps", "Sendedatenrate (Mesh)", "Mbit/s"),
    ("wifi_rate_rx_max_mbps", "Max. Empfangsdatenrate (Mesh)", "Mbit/s"),
    ("wifi_rate_tx_max_mbps", "Max. Sendedatenrate (Mesh)", "Mbit/s"),
)


def wlan_summary_attribute(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Create labeled, source-aware display rows from existing WLAN observations.

    The Mesh channel width describes the radio, not a client's negotiated
    bandwidth. Preserve competing readings; never derive missing values.
    """
    result: list[dict[str, Any]] = []
    for field, label, unit in _PRESENTATION_FIELDS:
        for row in rows:
            if row.get("field") != field:
                continue
            value = row.get("value")
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                continue
            display = f"{value} {unit}" if unit else str(value)
            result.append({
                "label": label,
                "value": display,
                "source": row.get("source"),
                "observed_at": row.get("observed_at"),
                **({"measurement_scope": row["measurement_scope"]}
                   if "measurement_scope" in row else {}),
            })
    return result
