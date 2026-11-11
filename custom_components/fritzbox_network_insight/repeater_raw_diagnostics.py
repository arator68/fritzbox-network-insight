"""Read-only, MAC-filtered repeater diagnostics from in-memory TR-064 snapshots."""
from __future__ import annotations

from xml.etree import ElementTree

from .device import normalize_mac


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def repeater_client_raw_snapshot(raw_store, mac: str, host: str | None = None) -> dict:
    """Return all fields for one MAC; never return unrelated clients or credentials."""
    target = normalize_mac(mac)
    if target is None:
        return {"error": "Invalid MAC address"}
    result = {"mac": target, "repeaters": {}}
    for repeater_host, snapshot in raw_store.data.items():
        if host and host != repeater_host:
            continue
        services = {}
        for service, actions in snapshot.get("services", {}).items():
            matching = []
            for association in actions.get("GetGenericAssociatedDeviceInfo", []):
                if not isinstance(association, dict):
                    continue
                if normalize_mac(association.get("NewAssociatedDeviceMACAddress")) == target:
                    matching.append({"source": "GetGenericAssociatedDeviceInfo", "fields": dict(association)})
            xml = actions.get("WLANDeviceListXML")
            if isinstance(xml, str):
                try:
                    root = ElementTree.fromstring(xml)
                    for item in root.iter():
                        if _local(item.tag) != "Item":
                            continue
                        fields = {_local(child.tag): (child.text or "").strip() for child in item}
                        if normalize_mac(fields.get("AssociatedDeviceMACAddress")) == target:
                            matching.append({"source": "WLANDeviceListXML", "fields": fields})
                except ElementTree.ParseError:
                    pass
            if matching:
                services[service] = matching
        result["repeaters"][repeater_host] = {
            "observed_at": snapshot.get("observed_at"),
            "services": services,
        }
    return result
