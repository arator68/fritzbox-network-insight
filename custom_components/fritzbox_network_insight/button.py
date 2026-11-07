"""Manual discovery controls for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator
from .discovery.manual import ManualDiscoveryRunner
from .discovery.ssdp import SsdpDiscoveryAdapter
from .discovery.snmp import SnmpDiscoveryAdapter
from .entity_id_migration import migrate_legacy_device_entity_id

_LOGGER = logging.getLogger(__name__)



def _migrate_discovery_button(
    hass: HomeAssistant, entry: ConfigEntry, mac: str, host: dict
) -> None:
    """Preserve the existing entity registry entry and user customizations."""
    compact_mac = mac.replace(":", "").lower()
    migrate_legacy_device_entity_id(
        hass,
        config_entry_id=entry.entry_id,
        platform="button",
        unique_id=f"host_{compact_mac}_manual_discovery",
        device_name=host.get("name") or mac,
        legacy_entity_names=("Geräteerkennung starten",),
        target_entity_id=f"button.fritzbox_network_insight_{compact_mac}_discover",
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add one global and one per-device explicit discovery button."""
    coordinator: FritzBoxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    runner = ManualDiscoveryRunner((
        SsdpDiscoveryAdapter(),
        SnmpDiscoveryAdapter(entry.options.get('snmp_devices', {})),
    ))
    known_macs: set[str] = set()
    buttons: list[ButtonEntity] = [DiscoverAllButton(coordinator, entry, runner)]
    for mac, host in sorted((coordinator.data or {}).items()):
        _migrate_discovery_button(hass, entry, mac, host)
        buttons.append(DiscoverHostButton(coordinator, entry, runner, mac))
        known_macs.add(mac)
    async_add_entities(buttons)

    @callback
    def _add_new_hosts() -> None:
        new_buttons: list[ButtonEntity] = []
        for mac in sorted((coordinator.data or {})):
            if mac not in known_macs:
                _migrate_discovery_button(
                    hass, entry, mac, (coordinator.data or {})[mac]
                )
                known_macs.add(mac)
                new_buttons.append(DiscoverHostButton(coordinator, entry, runner, mac))
        if new_buttons:
            async_add_entities(new_buttons)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_hosts))


class DiscoverAllButton(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], ButtonEntity
):
    """Request discovery for all known hosts."""

    _attr_has_entity_name = True
    _attr_name = "Geräteerkennung starten"
    _attr_icon = "mdi:radar"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
        runner: ManualDiscoveryRunner,
    ) -> None:
        super().__init__(coordinator)
        self._runner = runner
        self._attr_unique_id = f"{entry.entry_id}_manual_discovery_all"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FRITZ!Box {entry.data.get('host', '')}",
        )

    async def async_press(self) -> None:
        """Perform discovery only on explicit button press."""
        result = await self._runner.async_run(dict(self.coordinator.data or {}))
        await self.coordinator.async_record_manual_discovery(
            None, status=result.status, requested=result.requested, checked=result.checked, protocols=result.protocols, details=result.details
        )
        _LOGGER.info(
            "Manual discovery for all devices: %s (%d requested, %d checked)",
            result.status, result.requested, result.checked,
        )


class DiscoverHostButton(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], ButtonEntity
):
    """Request discovery for one stable MAC identity."""

    _attr_has_entity_name = True
    _attr_name = "Geräteerkennung starten"
    _attr_icon = "mdi:radar"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
        runner: ManualDiscoveryRunner,
        mac: str,
    ) -> None:
        super().__init__(coordinator)
        self._runner = runner
        self._mac = mac
        compact_mac = mac.replace(":", "").lower()
        self._attr_unique_id = f"host_{compact_mac}_manual_discovery"
        self.entity_id = f"button.fritzbox_network_insight_{compact_mac}_discover"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            connections={("mac", mac)},
        )

    async def async_press(self) -> None:
        """Perform discovery only for this device's MAC."""
        result = await self._runner.async_run(
            dict(self.coordinator.data or {}), self._mac
        )
        self.coordinator.record_manual_discovery(
            self._mac, status=result.status, requested=result.requested, checked=result.checked, protocols=result.protocols, details=result.details
        )
        _LOGGER.info(
            "Manual discovery for %s: %s (%d checked)",
            self._mac, result.status, result.checked,
        )
