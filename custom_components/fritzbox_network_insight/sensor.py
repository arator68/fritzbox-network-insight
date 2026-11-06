"""Sensors for FRITZ!Box Network Insight."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the overview sensor and one status sensor per discovered MAC."""
    coordinator: FritzBoxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_macs: set[str] = set()

    entities: list[SensorEntity] = [FritzBoxDeviceCountSensor(coordinator, entry)]
    for mac in sorted((coordinator.data or {}).keys()):
        entities.append(FritzBoxHostStatusSensor(coordinator, entry, mac))
        known_macs.add(mac)
    async_add_entities(entities)

    @callback
    def _add_new_hosts() -> None:
        """Add entities for devices first seen during a later scan."""
        new_entities: list[SensorEntity] = []
        for mac in sorted((coordinator.data or {}).keys()):
            if mac not in known_macs:
                known_macs.add(mac)
                new_entities.append(FritzBoxHostStatusSensor(coordinator, entry, mac))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_hosts))


class FritzBoxDeviceCountSensor(CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity):
    """Expose the number of hosts currently returned by the FRITZ!Box."""

    _attr_has_entity_name = True
    _attr_name = "Gefundene Geräte"
    _attr_icon = "mdi:lan"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_device_count"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FRITZ!Box {entry.data.get('host', '')}",
            manufacturer="AVM",
            model="FRITZ!Box",
            configuration_url=f"http://{entry.data.get('host', '')}",
        )

    @property
    def native_value(self) -> int:
        """Return the number of currently discovered hosts."""
        return len(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose a compact device list for dashboards and troubleshooting."""
        return {
            "devices": [
                {
                    "mac": host["mac"],
                    "name": host["name"],
                    "ip_address": host["ip_address"],
                    "active": host["active"],
                    "interface_type": host["interface_type"],
                }
                for host in (self.coordinator.data or {}).values()
            ]
        }


class FritzBoxHostStatusSensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Expose the current status and metadata of one MAC-identified host."""

    _attr_has_entity_name = True
    _attr_name = "Status"
    _attr_icon = "mdi:lan-connect"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
        mac: str,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        compact_mac = mac.replace(":", "").lower()
        self._attr_unique_id = f"host_{compact_mac}_status"
        host = (coordinator.data or {}).get(mac, {})
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=host.get("name") or mac,
            manufacturer="Unknown",
            model="Network device",
            connections={("mac", mac)},
        )

    @property
    def _host(self) -> dict[str, Any] | None:
        """Return the latest host record for this MAC."""
        return (self.coordinator.data or {}).get(self._mac)

    @property
    def native_value(self) -> str:
        """Return online, offline, unknown, or not seen in the latest scan."""
        host = self._host
        if host is None:
            return "nicht gefunden"
        if host["active"] is True:
            return "online"
        if host["active"] is False:
            return "offline"
        return "unbekannt"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the available metadata without inventing missing values."""
        host = self._host
        if host is None:
            return {"mac": self._mac, "seen_in_latest_scan": False}
        return {
            "mac": host["mac"],
            "name": host["name"],
            "ip_address": host["ip_address"],
            "active": host["active"],
            "interface_type": host["interface_type"],
            "seen_in_latest_scan": True,
        }
