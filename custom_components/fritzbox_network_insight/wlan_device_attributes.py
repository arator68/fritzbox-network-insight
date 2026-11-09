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
            observations.append({
                "field": key,
                "value": value,
                "source": observation.source,
                "observed_at": observation.observed_at,
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
