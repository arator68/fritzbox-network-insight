"""Separate per-device connection sensors derived from existing observations."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .connection_details import connection_details
from .coordinator import FritzBoxDataUpdateCoordinator

CONNECTION_FIELDS = ("type", "peer", "switch_port", "port_speed", "evidence")


class FritzBoxDeviceConnectionSensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Expose a connection property without performing additional scans."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FritzBoxDataUpdateCoordinator, mac: str, field: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._field = field
        compact = mac.replace(":", "").lower()
        self._attr_unique_id = f"host_{compact}_connection_{field}"
        self.entity_id = f"sensor.fritzbox_network_insight_{compact}_connection_{field}"
        self._attr_translation_key = f"connection_{field}"
        self._attr_icon = "mdi:lan-connect"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)}, connections={("mac", mac)},
        )
        if field == "port_speed":
            self._attr_native_unit_of_measurement = "Mbit/s"

    @property
    def _reading(self) -> tuple[str | int | None, dict[str, Any]]:
        host = (self.coordinator.data or {}).get(self._mac)
        if host is None:
            return None, {}
        connection = connection_details(
            self._mac, host,
            self.coordinator.get_combined_topology_snapshot(),
            self.coordinator.manual_links,
        )
        kind = connection.get("connection_type")
        if self._field == "type":
            return (kind if kind in ("lan", "wlan") else None), {}
        if self._field == "peer":
            return connection.get("connected_to"), {
                "connected_to_mac": connection.get("connected_to_mac"),
                "evidence": connection.get("connection_evidence"),
            }
        if self._field == "evidence":
            return connection.get("connection_evidence"), {}

        # Switch port and speed are meaningful only for Ethernet endpoints.
        if kind != "lan":
            return None, {}
        links = connection.get("connections") or []
        if len(links) != 1:
            return None, {}
        link = links[0]
        peer_mac = link.get("connected_to_mac")
        details = self.coordinator.device_details.get(self._mac)
        if details is None:
            return None, {}
        ports = [
            item.value for item in details.values("lan_switch_port")
            if isinstance(item.value, dict)
            and item.value.get("endpoint_access") == "ethernet"
            and item.value.get("switch_mac") == peer_mac
        ]
        # Require a unique matching port; avoid claiming a port from ambiguous FDB data.
        if len(ports) != 1:
            return None, {}
        port = ports[0]
        confirmed_bridge_port = link.get("peer_port")
        if confirmed_bridge_port is None:
            confirmed_bridge_port = link.get("connected_to_port")
        if (confirmed_bridge_port is not None
                and str(port.get("bridge_port")) != str(confirmed_bridge_port)
                and str(port.get("if_index")) != str(confirmed_bridge_port)):
            return None, {}
        interface_name = port.get("interface_name")
        match = re.search(r"(?:/|\b)(\d+)$", str(interface_name or ""))
        friendly_port = match.group(1) if match else interface_name
        attrs = {
            "switch_mac": peer_mac,
            "interface_name": interface_name,
            "bridge_port": port.get("bridge_port"),
            "evidence": link.get("evidence"),
            "port_evidence": port.get("evidence"),
        }
        if self._field == "switch_port":
            return friendly_port or port.get("bridge_port"), attrs
        speed = port.get("switch_port_reported_speed_mbps")
        if isinstance(speed, (int, float)) and not isinstance(speed, bool):
            return int(speed), {**attrs, "speed_source": port.get("switch_port_speed_source")}
        return None, attrs

    @property
    def native_value(self) -> str | int | None:
        return self._reading[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {key: value for key, value in self._reading[1].items() if value is not None}
