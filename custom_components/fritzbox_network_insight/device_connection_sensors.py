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

CONNECTION_FIELDS = ("role", "type", "peer", "switch_port", "port_speed", "evidence")


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
        if self._field == "role":
            kind = str(host.get("device_type") or "").strip().lower()
            return {"router": "Router", "switch": "Switch", "repeater": "Repeater", "access_point": "Access Point", "access point": "Access Point"}.get(kind, "Endgerät"), {"device_type_source": host.get("device_type_source")}
        snapshot = self.coordinator.get_combined_topology_snapshot()
        connection = connection_details(self._mac, host, snapshot)
        kind = connection.get("connection_type")
        # The router itself may lack an interface_type in the TR-064 host list.
        # Only a unique, explicitly confirmed LLDP link can establish LAN.
        link = connection.get("selected_connection")
        if (
            kind == "unknown"
            and link is not None
            and link.get("evidence") == "lldp_last_observed"
        ):
            kind = "lan"
        if self._field == "type":
            return (kind.upper() if kind in ("lan", "wlan") else None), {}
        if kind != "lan":
            return None, {}

        # LLDP confirms direct links; FDB identifies reachability only.
        # Never label FDB as proof of a physical cable.
        if self._field in ("peer", "evidence"):
            if link is not None:
                if self._field == "evidence":
                    return connection.get("connection_evidence"), {}
                return connection.get("connected_to"), {
                    "connected_to_mac": connection.get("connected_to_mac"),
                    "evidence": connection.get("connection_evidence"),
                }
            return None, {}

        # The peer-side LLDP port is usable only if the peer is a switch.
        # LLDP does not itself report port speed.
        if link is not None and link.get("evidence") == "lldp_last_observed":
            peer_mac = link.get("connected_to_mac")
            peer_is_switch = any(
                isinstance(node, dict)
                and str(node.get("mac") or "").upper() == str(peer_mac or "").upper()
                and str(node.get("device_type") or "").lower() == "switch"
                for node in snapshot.get("nodes", [])
            )
            if peer_is_switch:
                peer_port = link.get("peer_port")
                if self._field == "switch_port" and peer_port:
                    match = re.search(r"/([0-9]+)$", str(peer_port))
                    return (match.group(1) if match else str(peer_port)), {
                        "switch_mac": peer_mac,
                        "interface_name": peer_port,
                        "evidence": "lldp_last_observed",
                        "direct_connection": "confirmed",
                    }
                if self._field == "port_speed":
                    # Join the exact LLDP switch interface to that switch's
                    # independently observed IF-MIB port telemetry.
                    switch_details = self.coordinator.device_details.get(peer_mac)
                    matches = (
                        [item.value for item in switch_details.values("snmp_port_telemetry")
                         if isinstance(item.value, dict)
                         and item.value.get("interface_name") == peer_port]
                        if switch_details is not None and peer_port else []
                    )
                    attrs = {
                        "switch_mac": peer_mac,
                        "interface_name": peer_port,
                        "evidence": "lldp_last_observed",
                        "direct_connection": "confirmed",
                    }
                    if len(matches) == 1:
                        port = matches[0]
                        speed = port.get("reported_speed_mbps")
                        if isinstance(speed, (int, float)) and not isinstance(speed, bool) and speed > 0:
                            return int(speed), {
                                **attrs, "speed_source": port.get("speed_source"),
                                "oper_status": port.get("oper_status"),
                            }
                    return None, attrs

        # Reachability alone cannot establish an endpoint port or speed.
        return None, {}

    @property
    def native_value(self) -> str | int | None:
        return self._reading[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {key: value for key, value in self._reading[1].items() if value is not None}
