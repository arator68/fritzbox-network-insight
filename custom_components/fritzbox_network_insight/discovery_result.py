"""Diagnostic sensors for explicit manual discovery requests."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator


class ManualDiscoveryResultSensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Expose the latest explicit discovery attempt, not a protocol support claim."""

    _attr_has_entity_name = True
    _attr_name = "Ergebnis Geräteerkennung"
    _attr_icon = "mdi:radar"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
        mac: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        if mac is None:
            self._attr_unique_id = f"{entry.entry_id}_manual_discovery_result"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry.entry_id)},
                name=f"FRITZ!Box {entry.data.get('host', '')}",
            )
        else:
            compact_mac = mac.replace(":", "").lower()
            self._attr_unique_id = f"host_{compact_mac}_manual_discovery_result"
            self.entity_id = (
                f"sensor.fritzbox_network_insight_{compact_mac}_discovery_result"
            )
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, mac)},
                connections={("mac", mac)},
            )

    @property
    def native_value(self) -> str:
        """Return the most recent result, or not_started after restart."""
        record = self.coordinator.discovery_results.get(self._mac)
        return str(record["status"]) if record else "not_started"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose only summary counts and time, never credentials."""
        record = self.coordinator.discovery_results.get(self._mac)
        if record is None:
            return {"last_run": None, "requested": 0, "checked": 0}
        return dict(record)
