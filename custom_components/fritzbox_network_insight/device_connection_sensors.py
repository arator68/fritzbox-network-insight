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
        # The router itself may lack an interface_type in the TR-064 host list.
        # Only a unique, explicitly confirmed LLDP link can establish LAN.
        direct = connection.get("connections") or []
        link = direct[0] if len(direct) == 1 else None
        if (
            kind == "unknown"
            and link is not None
            and link.get("evidence") == "lldp_last_observed"
        ):
            kind = "lan"
        if self._field == "type":
            return (kind if kind in ("lan", "wlan") else None), {}
        if kind != "lan":
            return None, {}

        # LLDP confirms direct links; FDB identifies reachability only.
        # Never label FDB as proof of a physical cable.
        reachable = connection.get("reachable_via_switch_ports") or []
        fdb = reachable[0] if len(reachable) == 1 else None
        if self._field in ("peer", "evidence"):
            if link is not None:
                if self._field == "evidence":
                    return connection.get("connection_evidence"), {}
                return connection.get("connected_to"), {
                    "connected_to_mac": connection.get("connected_to_mac"),
                    "evidence": connection.get("connection_evidence"),
                }
            if fdb is None or direct:
                return None, {}
            switch_mac = fdb["switch_mac"]
            if self._field == "evidence":
                return "fdb_reachable_via_port", {"direct_connection": "unconfirmed"}
            nodes = self.coordinator.get_combined_topology_snapshot().get("nodes", [])
            name = next(
                (node.get("name") for node in nodes
                 if isinstance(node, dict)
                 and str(node.get("mac") or "").upper() == switch_mac
                 and node.get("name")),
                switch_mac,
            )
            return name, {
                "connected_to_mac": switch_mac,
                "evidence": "fdb_reachable_via_port",
                "direct_connection": "unconfirmed",
            }

        # The peer-side LLDP port is usable only if the peer is a switch.
        # LLDP does not itself report port speed.
        if link is not None and link.get("evidence") == "lldp_last_observed":
            snapshot = self.coordinator.get_combined_topology_snapshot()
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

        # The port is the observed switch ingress, not necessarily a direct
        # endpoint cable. Require exactly one matching FDB observation.
        if fdb is None:
            return None, {}
        switch_mac = fdb["switch_mac"]
        details = self.coordinator.device_details.get(self._mac)
        if details is None:
            return None, {}
        ports = [
            item.value for item in details.values("lan_switch_port")
            if isinstance(item.value, dict)
            and item.value.get("endpoint_access") == "ethernet"
            and item.value.get("switch_mac") == switch_mac
            and item.value.get("interface_name") == fdb.get("interface_name")
        ]
        if len(ports) != 1:
            return None, {}
        port = ports[0]
        interface_name = port.get("interface_name")
        match = re.search(r"(?:/|\\b)(\\d+)$", str(interface_name or ""))
        friendly_port = match.group(1) if match else interface_name
        attrs = {
            "switch_mac": switch_mac,
            "interface_name": interface_name,
            "bridge_port": port.get("bridge_port"),
            "evidence": "fdb_reachable_via_port",
            "direct_connection": "unconfirmed",
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
