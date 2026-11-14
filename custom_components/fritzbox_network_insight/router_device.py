"""Resolve the configured router to its MAC-identified Home Assistant device."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def router_device_info(coordinator, entry: ConfigEntry) -> DeviceInfo:
    """Reuse a physical router only when its configured address matches uniquely.

    Do not infer the router from its hostname, vendor, or a switch neighbor.
    Other configured FRITZ!Boxes remain independent.
    """
    address = str(entry.data.get("host") or "").strip().lower()
    matches = [
        mac for mac, host in (coordinator.data or {}).items()
        if str(host.get("ip_address") or "").strip().lower() == address
    ]
    if len(matches) == 1:
        mac = matches[0]
        return DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={("mac", mac)},
        )
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"FRITZ!Box {entry.data.get('host', '')}",
        manufacturer="AVM",
        model="FRITZ!Box",
    )
