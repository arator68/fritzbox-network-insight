"""Select eligible Home Assistant network adapters for Easy Smart discovery."""
from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any


def select_interfaces(adapters: list[dict[str, Any]]) -> list[tuple[str, bytes]]:
    """Return unique enabled IPv4 addresses with valid unicast MACs."""
    result = {}
    for adapter in adapters:
        if not adapter.get("enabled"):
            continue
        try:
            mac = bytes.fromhex(str(adapter.get("mac") or "").replace(":", "").replace("-", ""))
        except ValueError:
            continue
        if len(mac) != 6 or not any(mac) or mac[0] & 1:
            continue
        for entry in adapter.get("ipv4") or []:
            try:
                ip = IPv4Address(entry.get("address"))
            except (ValueError, TypeError, AttributeError):
                continue
            if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_link_local or int(ip) == 0xffffffff:
                continue
            result.setdefault(str(ip), mac)
    return list(result.items())


async def async_discover(hass):
    """Run bounded discovery on enabled adapters, outside the event loop."""
    from homeassistant.components import network
    from .tplink_discovery import discover_switches

    adapters = await network.async_get_adapters(hass)
    found = {}
    for ip, mac in select_interfaces(adapters):
        identities = await hass.async_add_executor_job(discover_switches, ip, mac)
        for identity in identities:
            found[identity.mac] = identity
    return list(found.values())
