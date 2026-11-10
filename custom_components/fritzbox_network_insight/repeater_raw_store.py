"""Bounded, persistent read-only TR-064 repeater response snapshots.

Snapshots contain AVM response payloads, never credentials or HTTP headers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPDigestAuthHandler, HTTPPasswordMgrWithDefaultRealm, build_opener

from fritzconnection import FritzConnection
from homeassistant.helpers.storage import Store

MAX_HISTORY = 12
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
    """Keep the last successful snapshot and bounded history per repeater."""

    def __init__(self, hass, entry_id: str) -> None:
        self._store = Store(hass, 1, f"fritzbox_network_insight.repeater_raw.{entry_id}")
        self.data: dict[str, list[dict]] = {}

    async def async_load(self) -> None:
        try:
            loaded = await self._store.async_load()
            if isinstance(loaded, dict):
                self.data = {
                    host: snapshots[-MAX_HISTORY:]
                    for host, snapshots in loaded.items()
                    if isinstance(host, str) and isinstance(snapshots, list)
                }
        except Exception:
            self.data = {}

    async def async_add(self, host: str, snapshot: dict) -> None:
        history = self.data.setdefault(host, [])
        history.append(snapshot)
        del history[:-MAX_HISTORY]
        await self._store.async_save(self.data)
