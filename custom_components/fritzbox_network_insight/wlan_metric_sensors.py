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
    """Find an actual measurement, without deriving or merging radio scopes."""
    field, scope, _unit = WLAN_METRICS[metric]
    for row in rows:
        if row.get("field") != field:
            continue
        if scope is not None and row.get("measurement_scope") != scope:
            continue
        value = row.get("value")
        if metric in ("mesh_channel_width", "mesh_peer_channel_width") and isinstance(value, str):
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
        if metric in ("mesh_signal_rx_raw", "mesh_signal_tx_raw") and value == 255:
            continue
        return {"value": value, "source": row.get("source"), "observed_at": row.get("observed_at"), **({"measurement_scope": scope} if scope else {})}
    return None
