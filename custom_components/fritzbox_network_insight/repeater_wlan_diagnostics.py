"""Read-only TR-064 diagnostics for one MAC on one repeater.

AVM's X_AVM-DE_Speed has no documented RX/TX direction here.
Never substitute it for Mesh RX or TX.
"""
from __future__ import annotations

from fritzconnection import FritzConnection

from .device import normalize_mac
from .wlan_details import fetch_wlan_devices


def fetch_repeater_wlan_diagnostics(
    host: str, username: str, password: str, target_mac: str, timeout: int = 10
) -> dict[str, int]:
    """Return client-specific measurements, preserving their distinct origins."""
    target = normalize_mac(target_mac)
    if target is None:
        return {}

    results: dict[str, int] = {}

    # The list endpoint can return an undirected X_AVM-DE_Speed for this MAC.
    # Failure of the optional list must not prevent the association lookup.
    try:
        records = fetch_wlan_devices(host, username, password, timeout).get(target, {})
    except Exception:
        records = {}
    for fields in records.values():
        for key in (
            "wifi_speed_mbps", "wifi_speed_rx_mbps",
            "wifi_speed_max_mbps", "wifi_speed_rx_max_mbps",
        ):
            value = fields.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                results.setdefault("repeater_tr064_" + key, value)

    # GetSpecificAssociatedDeviceInfo may report a DIFFERENT, undirected
    # speed at a different moment. Do not equate it to the device-list speed.
    connection = FritzConnection(
        address=host, user=username, password=password, timeout=timeout
    )
    for instance in (1, 2, 3):
        try:
            record = connection.call_action(
                f"WLANConfiguration{instance}",
                "GetSpecificAssociatedDeviceInfo",
                NewAssociatedDeviceMACAddress=target,
            )
        except Exception:
            # AVM returns UPnP 714 when the MAC is not on this instance.
            continue
        speed = record.get("NewX_AVM-DE_Speed")
        try:
            speed = int(speed)
        except (TypeError, ValueError):
            continue
        if speed >= 0:
            results.setdefault("repeater_tr064_associated_speed_mbps", speed)
    return results


def fetch_repeater_clients(
    host: str, username: str, password: str, timeout: int = 10
) -> dict[str, dict[str, int]]:
    """Read every associated client, indexed by MAC, without inferring RX/TX.

    The AVM WLAN device list can contain clients from several radio instances.
    A MAC is published once even if several instances return the same client.
    """
    clients: dict[str, dict[str, int]] = {}
    records = fetch_wlan_devices(host, username, password, timeout)
    for mac, instances in records.items():
        fields_out: dict[str, int] = {}
        for fields in instances.values():
            for key in (
                "wifi_speed_mbps", "wifi_speed_rx_mbps",
                "wifi_speed_max_mbps", "wifi_speed_rx_max_mbps",
                "wifi_signal_strength", "wifi_channel", "wifi_channel_width",
            ):
                value = fields.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    fields_out.setdefault("repeater_tr064_" + key, value)
        if fields_out:
            clients[mac] = fields_out
    return clients
