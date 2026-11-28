"""Select eligible Home Assistant network adapters for Easy Smart discovery."""
from __future__ import annotations

from ipaddress import IPv4Address
from typing import Any
from pathlib import Path


def read_interface_mac(name: str) -> str | None:
    """Read the actual Linux interface address without guessing."""
    if not name or name in ('.', '..') or '/' in name:
        return None
    try:
        return (Path('/sys/class/net') / name / 'address').read_text().strip()
    except OSError:
        return None


def select_interfaces(adapters: list[dict[str, Any]], mac_lookup=read_interface_mac) -> list[tuple[str, bytes]]:
    """Return unique enabled IPv4 addresses with valid unicast MACs."""
    result = {}
    for adapter in adapters:
        if not adapter.get("enabled"):
            continue
        try:
            mac = bytes.fromhex(str(mac_lookup(adapter.get("name") or "") or "").replace(":", "").replace("-", ""))
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
    interfaces = await hass.async_add_executor_job(select_interfaces, adapters)
    for ip, mac in interfaces:
        identities = await hass.async_add_executor_job(discover_switches, ip, mac)
        for identity in identities:
            found[identity.mac] = identity
    return list(found.values())


def enrich_host(host, identity, existing_identification=None):
    """Add identity metadata only when no stronger identification exists."""
    if (identity is None or existing_identification is not None
            or host.get("detected_device_type") or host.get("mesh_role")
            or str(host.get("mac", "")).upper() != identity.mac.upper()):
        return
    host.update({
        "detected_device_type": "switch",
        "detected_device_type_source": "tplink_easy_smart_discovery",
        "device_manufacturer": "TP-Link",
        "device_model": identity.model,
    })
