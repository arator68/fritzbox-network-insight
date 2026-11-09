"""Optional TR-064 WLAN association observations.

Reads only fields actually returned by AVM. No band guessing from channel,
and a signal-strength value is not labelled as RX or TX dBm.
"""
from __future__ import annotations

from urllib.parse import urljoin, urlparse
from urllib.request import HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener
from xml.etree import ElementTree

from fritzconnection import FritzConnection

from .device import normalize_mac


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_wlan_list(xml: str | bytes) -> dict[str, dict]:
    """Parse AVM WLANDeviceList XML by exact associated-device MAC."""
    root = ElementTree.fromstring(xml)
    result: dict[str, dict] = {}
    fields_map = {
        "X_AVM-DE_Speed": "wifi_speed_mbps",
        "X_AVM-DE_SpeedRX": "wifi_speed_rx_mbps",
        "X_AVM-DE_SpeedMax": "wifi_speed_max_mbps",
        "X_AVM-DE_SpeedRXMax": "wifi_speed_rx_max_mbps",
        "X_AVM-DE_SignalStrength": "wifi_signal_strength",
        "AssociatedDeviceChannel": "wifi_channel",
        "X_AVM-DE_ChannelWidth": "wifi_channel_width",
    }
    for item in root.iter():
        if _local(item.tag) != "Item":
            continue
        fields = {_local(child.tag): (child.text or "").strip() for child in item}
        mac = normalize_mac(fields.get("AssociatedDeviceMACAddress"))
        if mac is None:
            continue
        values: dict = {}
        for source_key, target_key in fields_map.items():
            try:
                raw = fields.get(source_key)
                if raw is not None and raw != "":
                    number = int(raw)
                    if number >= 0 and (target_key != "wifi_channel" or number > 0):
                        values[target_key] = number
            except ValueError:
                continue
        # The newer AVM XML schema can report the band explicitly.
        # Never derive it from the WLANConfiguration instance number.
        band = fields.get("X_AVM-DE_FrequencyBand", "").strip()
        if band in {"2400", "5000", "6000"}:
            values["wifi_frequency_band_mhz"] = int(band)
        guest = fields.get("AssociatedDeviceGuest", "").lower()
        if guest in {"0", "false"}:
            values["wifi_guest"] = False
        elif guest in {"1", "true"}:
            values["wifi_guest"] = True
        if values:
            result[mac] = values
    return result


def fetch_wlan_devices(host: str, username: str, password: str, timeout: int = 10) -> dict[str, dict]:
    """Blocking optional AVM WLAN list fetch; invoke only in HA executor."""
    connection = FritzConnection(address=host, user=username, password=password, timeout=timeout)
    records: dict[str, dict] = {}
    # Association membership provides the actual radio band for each MAC.
    # The AVM WLANDeviceListPath response can contain clients across radios;
    # its originating instance must not be treated as a band identifier.
    mac_to_band: dict[str, int] = {}
    for instance in (1, 2, 3, 4):
        service = f"WLANConfiguration{instance}"
        try:
            info = connection.call_action(service, "GetInfo")
            band_raw = str(info.get("NewX_AVM-DE_FrequencyBand") or "").strip()
            band = int(band_raw) if band_raw in {"2400", "5000", "6000"} else None
            total_response = connection.call_action(service, "GetTotalAssociations")
            total = int(total_response.get("NewTotalAssociations") or 0)
            if band is None:
                continue
            for index in range(min(max(total, 0), 512)):
                try:
                    association = connection.call_action(
                        service, "GetGenericAssociatedDeviceInfo",
                        NewAssociatedDeviceIndex=index,
                    )
                    mac = normalize_mac(association.get("NewAssociatedDeviceMACAddress"))
                    if mac:
                        mac_to_band[mac] = band
                except Exception:  # noqa: BLE001 - optional AVM service/action
                    continue
        except Exception:  # noqa: BLE001 - unsupported optional AVM service
            continue
    for instance in (1, 2, 3, 4):
        try:
            response = connection.call_action(
                f"WLANConfiguration{instance}", "X_AVM-DE_GetWLANDeviceListPath"
            )
            path = response.get("NewX_AVM-DE_WLANDeviceListPath")
            if not isinstance(path, str) or not path:
                continue
            url = urljoin(f"http://{host}:49000/", path)
            parsed = urlparse(url)
            if parsed.hostname != host or parsed.scheme not in {"http", "https"}:
                continue
            manager = HTTPPasswordMgrWithDefaultRealm()
            manager.add_password(None, url, username, password)
            opener = build_opener(HTTPDigestAuthHandler(manager))
            with opener.open(url, timeout=timeout) as stream:
                values = parse_wlan_list(stream.read())
            for mac, properties in values.items():
                if mac in mac_to_band:
                    properties["wifi_frequency_band_mhz"] = mac_to_band[mac]
                # Keep distinct per-instance observations; no inferred radio band.
                records.setdefault(mac, {})[f"wlan_configuration_{instance}"] = properties
        except Exception:  # noqa: BLE001 - unsupported optional AVM service or XML
            # Different FRITZ!OS releases expose different WLAN instances.
            continue
    return records
