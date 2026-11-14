"""Resolve the configured router to its MAC-identified Home Assistant device."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN


def router_mac(coordinator, entry: ConfigEntry) -> str | None:
    """Return a unique host MAC for the configured router IP, if known."""
    address = str(entry.data.get("host") or "").strip().lower()
    matches = [
        mac for mac, host in (coordinator.data or {}).items()
        if str(host.get("ip_address") or "").strip().lower() == address
    ]
    return matches[0] if len(matches) == 1 else None


def router_device_info(coordinator, entry: ConfigEntry) -> DeviceInfo:
    """Reuse a physical router only when its configured address matches uniquely.

    Do not infer the router from its hostname, vendor, or a switch neighbor.
    Other configured FRITZ!Boxes remain independent.
    """
    mac = router_mac(coordinator, entry)
    if mac is not None:
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


def migrate_router_device(hass, coordinator, entry: ConfigEntry) -> int:
    """Move only this entry's central entities to its already existing physical device.

    Never remove a device still used by any entity or another config entry.
    The operation is safe to repeat after a restart.
    """
    mac = router_mac(coordinator, entry)
    if mac is None:
        return 0
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    old = devices.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    physical = devices.async_get_device(identifiers={(DOMAIN, mac)})
    if physical is None:
        physical = devices.async_get_device(connections={("mac", mac)})
    if old is None or physical is None or old.id == physical.id:
        return 0
    moved = 0
    for entity in list(er.async_entries_for_device(entities, old.id)):
        if entity.config_entry_id != entry.entry_id or entity.platform != DOMAIN:
            continue
        entities.async_update_entity(entity.entity_id, device_id=physical.id)
        moved += 1
    # Never delete a device belonging to another integration or still in use.
    if (
        not er.async_entries_for_device(entities, old.id)
        and set(old.config_entries).issubset({entry.entry_id})
    ):
        devices.async_remove_device(old.id)
    return moved
