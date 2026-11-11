"""Select only explicit, numeric WLAN measurements for HA sensors."""
from __future__ import annotations

import re
from typing import Any

# key -> (raw field, expected scope, unit)
WLAN_METRICS = {
    "channel": ("wifi_channel", None, None),
    "mesh_channel": ("mesh_wifi_channel", None, None),
    "mesh_peer_channel_width": ("mesh_peer_interface_channel_width_raw", None, "MHz"),
    "mesh_signal_rx_raw": ("mesh_rx_rcpi_raw", None, None),
    "mesh_signal_tx_raw": ("mesh_tx_rcpi_raw", None, None),
    "channel_width": ("wifi_channel_width", "tr064_wlan_device", "MHz"),
    "mesh_channel_width": ("mesh_radio_channel_width", "mesh_radio_channel", "MHz"),
    "rx_rate": ("wifi_rate_rx_mbps", None, "Mbit/s"),
    "tx_rate": ("wifi_rate_tx_mbps", None, "Mbit/s"),
    "signal_strength": ("wifi_signal_strength", None, None),
}


def metric_observation(rows: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    """Select a valid measurement with its actual source and measurement scope."""
    field, scope, _unit = WLAN_METRICS[metric]
    candidates = {
        "channel": ((field, scope), ("mesh_peer_interface_channel", None), ("mesh_wifi_channel", None)),
        "channel_width": ((field, scope), ("mesh_peer_interface_channel_width_raw", None)),
        "signal_strength": (("mesh_rx_rcpi_raw", None), (field, scope)),
    }.get(metric, ((field, scope),))
    for candidate_field, candidate_scope in candidates:
        for row in rows:
            if row.get("field") != candidate_field:
                continue
            if candidate_scope is not None and row.get("measurement_scope") != candidate_scope:
                continue
            value = row.get("value")
            if metric in ("channel_width", "mesh_channel_width", "mesh_peer_channel_width") and isinstance(value, str):
                match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*MHz\s*", value)
                if not match:
                    continue
                value = float(match.group(1))
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if metric in ("channel_width", "mesh_channel_width", "mesh_peer_channel_width") and value <= 0:
                continue
            if metric in ("channel", "mesh_channel") and not 1 <= value <= 233:
                continue
            if candidate_field in ("mesh_rx_rcpi_raw", "mesh_tx_rcpi_raw") and value == 255:
                continue
            return {
                "value": value,
                "source": row.get("source"),
                "observed_at": row.get("observed_at"),
                "source_field": candidate_field,
                "measurement_scope": row.get("measurement_scope") or (
                    "mesh_peer_interface" if candidate_field.startswith("mesh_peer_")
                    else "mesh_signal_raw" if candidate_field == "mesh_rx_rcpi_raw"
                    else "mesh_radio" if candidate_field == "mesh_wifi_channel"
                    else "tr064_wlan_device" if candidate_field.startswith("wifi_")
                    else None
                ),
            }
    return None
