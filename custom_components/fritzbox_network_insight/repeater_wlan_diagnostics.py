"""Read-only, opt-in TR-064 diagnostics for one WLAN client on one repeater."""
from __future__ import annotations

from fritzconnection import FritzConnection

from .device import normalize_mac
from .wlan_details import fetch_wlan_devices


def fetch_repeater_wlan_diagnostics(
    host: str, username: str, password: str, target_mac: str, timeout: int = 10
) -> dict[str, int]:
    """Return only values explicitly reported for the exact target MAC.

    X_AVM-DE_GetWLANConnectionInfo has no client selector, so it is NOT used
    as evidence of a particular client's link rates.
    """
    target = normalize_mac(target_mac)
    if target is None:
        return {}
    results: dict[str, int] = {}
    # Reuse the existing MAC-indexed WLANDeviceList parser.
    for fields in fetch_wlan_devices(host, username, password, timeout).get(target, {}).values():
        for key in ("wifi_speed_mbps", "wifi_speed_rx_mbps",
                    "wifi_speed_max_mbps", "wifi_speed_rx_max_mbps"):
            value = fields.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                results.setdefault("repeater_tr064_" + key, value)

    # The standard association call also reports a client-specific speed.
    connection = FritzConnection(address=host, user=username, password=password, timeout=timeout)
    for instance in (1, 2, 3):
        try:
            record = connection.call_action(
                f"WLANConfiguration{instance}", "GetSpecificAssociatedDeviceInfo",
                NewAssociatedDeviceMACAddress=target,
            )
        except Exception:  # Unsupported service or client not associated here.
            continue
        speed = record.get("NewX_AVM-DE_Speed")
        try:
            speed = int(speed)
        except (TypeError, ValueError):
            continue
        if speed >= 0:
            results.setdefault("repeater_tr064_associated_speed_mbps", speed)
    return results
