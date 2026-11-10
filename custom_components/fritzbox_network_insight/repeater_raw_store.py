"""Read-only TR-064 repeater responses retained only in memory."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener

from fritzconnection import FritzConnection
from .wlan_details import parse_wlan_list

MAX_PAYLOAD_CHARS = 1_000_000


def fetch_repeater_raw(host: str, username: str, password: str, timeout: int = 10) -> dict:
    """Fetch available WLAN service responses without discarding unknown fields."""
    connection = FritzConnection(address=host, user=username, password=password, timeout=timeout)
    result = {"observed_at": datetime.now(timezone.utc).isoformat(), "services": {}}
    for instance in (1, 2, 3, 4):
        service = f"WLANConfiguration{instance}"
        actions = {}
        for action in ("GetInfo", "GetTotalAssociations", "X_AVM-DE_GetWLANDeviceListPath"):
            try:
                response = connection.call_action(service, action)
                actions[action] = dict(response)
                if action == "GetTotalAssociations":
                    total = min(max(int(response.get("NewTotalAssociations") or 0), 0), 512)
                    associations = []
                    for index in range(total):
                        try:
                            associations.append(dict(connection.call_action(
                                service, "GetGenericAssociatedDeviceInfo",
                                NewAssociatedDeviceIndex=index,
                            )))
                        except Exception:
                            associations.append({"index": index, "error": "unavailable"})
                    actions["GetGenericAssociatedDeviceInfo"] = associations
                if action == "X_AVM-DE_GetWLANDeviceListPath":
                    path = response.get("NewX_AVM-DE_WLANDeviceListPath")
                    if isinstance(path, str) and path:
                        url = urljoin(f"http://{host}:49000/", path)
                        parsed = urlparse(url)
                        if parsed.hostname == host and parsed.scheme in ("http", "https"):
                            manager = HTTPPasswordMgrWithDefaultRealm()
                            manager.add_password(None, url, username, password)
                            opener = build_opener(HTTPDigestAuthHandler(manager))
                            with opener.open(url, timeout=timeout) as stream:
                                payload = stream.read(MAX_PAYLOAD_CHARS + 1)
                            if len(payload) <= MAX_PAYLOAD_CHARS:
                                actions["WLANDeviceListXML"] = payload.decode("utf-8", errors="replace")
                            else:
                                actions["WLANDeviceListXML_error"] = "payload_too_large"
            except Exception:
                # Unsupported actions are expected on some FRITZ!OS versions.
                continue
        if actions:
            result["services"][service] = actions
    if not result["services"]:
        raise ValueError("No repeater WLAN TR-064 data available")
    return result


class RepeaterRawStore:
    """Keep only the latest successful response per repeater in memory."""

    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def update(self, host: str, snapshot: dict) -> None:
        self.data[host] = snapshot

    def client_values(self) -> dict[str, dict[str, dict[str, int]]]:
        """Derive existing client fields from cached XML without network requests."""
        result: dict[str, dict[str, dict[str, int]]] = {}
        keys = (
            "wifi_speed_mbps", "wifi_speed_rx_mbps",
            "wifi_speed_max_mbps", "wifi_speed_rx_max_mbps",
            "wifi_signal_strength", "wifi_channel", "wifi_channel_width",
        )
        for host, snapshot in self.data.items():
            clients: dict[str, dict[str, int]] = {}
            for actions in snapshot.get("services", {}).values():
                xml = actions.get("WLANDeviceListXML")
                if not isinstance(xml, str):
                    continue
                try:
                    records = parse_wlan_list(xml)
                except Exception:
                    continue
                for mac, fields in records.items():
                    values = clients.setdefault(mac, {})
                    for key in keys:
                        value = fields.get(key)
                        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                            values.setdefault("repeater_tr064_" + key, value)
            result[host] = clients
        return result

    def summary(self, host: str) -> dict:
        """Small, safe status summary; never expose raw XML in entity attributes."""
        snapshot = self.data.get(host)
        if snapshot is None:
            return {"available": False}
        services = snapshot.get("services", {})
        return {
            "available": True,
            "observed_at": snapshot.get("observed_at"),
            "wlan_services": sorted(services),
            "client_count": len(self.client_values().get(host, {})),
            "raw_xml_lists": sum(
                isinstance(actions.get("WLANDeviceListXML"), str)
                for actions in services.values()
            ),
        }
