"""Sensors for FRITZ!Box Network Insight."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator
from .entity_id_migration import (
    migrate_legacy_status_entity_id,
    migrate_legacy_device_entity_id,
)
from .discovery_result import ManualDiscoveryResultSensor
from .wlan_device_attributes import wlan_details_attribute
from .wlan_metric_sensors import WLAN_METRICS, metric_observation

VISIBLE_WLAN_METRICS = (
    "channel", "channel_width", "signal_strength",
    "mesh_channel_width", "rx_rate", "tx_rate", "mesh_signal_tx_raw",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the overview sensor and one status sensor per discovered MAC."""
    coordinator: FritzBoxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_macs: set[str] = set()
    wlan_macs: set[str] = set()
    registered_wlan_metrics: set[tuple[str, str]] = set()
    registry = er.async_get(hass)
    obsolete = ("mesh_channel", "mesh_peer_channel_width", "mesh_signal_rx_raw")
    for registered in list(er.async_entries_for_config_entry(registry, entry.entry_id)):
        if registered.domain == "sensor" and registered.platform == DOMAIN and any(
            registered.unique_id.endswith(f"_wlan_{key}") for key in obsolete
        ):
            registry.async_remove(registered.entity_id)

    def _wlan_entities(mac: str) -> list[SensorEntity]:
        host = (coordinator.data or {}).get(mac)
        if not _is_wlan(host) or host.get("active") is not True:
            return []
        details = coordinator.device_details.get(mac)
        if details is None:
            return []
        rows = wlan_details_attribute(details, host.get("interface_type"))
        result: list[SensorEntity] = []
        for key in VISIBLE_WLAN_METRICS:
            identity = (mac, key)
            if identity not in registered_wlan_metrics and metric_observation(rows, key) is not None:
                registered_wlan_metrics.add(identity)
                result.append(FritzBoxWlanMetricSensor(coordinator, mac, key))
        return result

    # Migrate registered legacy IDs before creating/adding entities.
    for mac, host in sorted((coordinator.data or {}).items()):
        compact_mac = mac.replace(":", "").lower()
        migrate_legacy_status_entity_id(
            hass,
            config_entry_id=entry.entry_id,
            unique_id=f"host_{compact_mac}_status",
            device_name=host.get("name") or mac,
            target_entity_id=f"sensor.fritzbox_network_insight_{compact_mac}_status",
        )
        migrate_legacy_device_entity_id(
            hass,
            config_entry_id=entry.entry_id,
            platform="sensor",
            unique_id=f"host_{compact_mac}_manual_discovery_result",
            device_name=host.get("name") or mac,
            legacy_entity_names=("Ergebnis Geräteerkennung",),
            target_entity_id=(
                f"sensor.fritzbox_network_insight_{compact_mac}_discovery_result"
            ),
        )

    entities: list[SensorEntity] = [
        FritzBoxDeviceCountSensor(coordinator, entry),
        FritzBoxTopologySensor(coordinator, entry),
        FritzBoxFdbTopologySensor(coordinator, entry),
        FritzBoxCombinedTopologySensor(coordinator, entry),
        ManualDiscoveryResultSensor(coordinator, entry),
    ]
    for mac in sorted((coordinator.data or {}).keys()):
        entities.append(FritzBoxHostStatusSensor(coordinator, entry, mac))
        entities.append(ManualDiscoveryResultSensor(coordinator, entry, mac))
        if _is_wlan((coordinator.data or {}).get(mac)):
            entities.extend(_wlan_entities(mac))
            wlan_macs.add(mac)
        known_macs.add(mac)
    async_add_entities(entities)

    @callback
    def _add_new_hosts() -> None:
        """Add entities for devices first seen during a later scan."""
        new_entities: list[SensorEntity] = []
        for mac in sorted((coordinator.data or {}).keys()):
            if mac not in known_macs:
                compact_mac = mac.replace(":", "").lower()
                host = (coordinator.data or {}).get(mac, {})
                migrate_legacy_status_entity_id(
                    hass,
                    config_entry_id=entry.entry_id,
                    unique_id=f"host_{compact_mac}_status",
                    device_name=host.get("name") or mac,
                    target_entity_id=(
                        f"sensor.fritzbox_network_insight_{compact_mac}_status"
                    ),
                )
                migrate_legacy_device_entity_id(
                    hass,
                    config_entry_id=entry.entry_id,
                    platform="sensor",
                    unique_id=f"host_{compact_mac}_manual_discovery_result",
                    device_name=host.get("name") or mac,
                    legacy_entity_names=("Ergebnis Geräteerkennung",),
                    target_entity_id=(
                        f"sensor.fritzbox_network_insight_{compact_mac}_discovery_result"
                    ),
                )
                known_macs.add(mac)
                new_entities.append(FritzBoxHostStatusSensor(coordinator, entry, mac))
                new_entities.append(ManualDiscoveryResultSensor(coordinator, entry, mac))
            if mac not in wlan_macs and _is_wlan((coordinator.data or {}).get(mac)):
                wlan_macs.add(mac)
                new_entities.extend(_wlan_entities(mac))
        for mac in sorted(wlan_macs):
            new_entities.extend(_wlan_entities(mac))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_hosts))


def _is_wlan(host: dict[str, Any] | None) -> bool:
    return str((host or {}).get("interface_type") or "").strip().lower() in {"802.11", "wlan", "wifi", "wi-fi"}


class FritzBoxWlanMetricSensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """A numeric WLAN measurement, retaining its original provenance."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator: FritzBoxDataUpdateCoordinator, mac: str, metric: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._metric = metric
        compact_mac = mac.replace(":", "").lower()
        self._attr_unique_id = f"host_{compact_mac}_wlan_{metric}"
        self.entity_id = f"sensor.fritzbox_network_insight_{compact_mac}_wlan_{metric}"
        self._attr_translation_key = f"wlan_{metric}"
        self._attr_native_unit_of_measurement = WLAN_METRICS[metric][2]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)}, connections={("mac", mac)},
        )

    @property
    def _observation(self) -> dict[str, Any] | None:
        host = (self.coordinator.data or {}).get(self._mac)
        if not _is_wlan(host) or host.get("active") is not True:
            return None
        details = self.coordinator.device_details.get(self._mac)
        if details is None:
            return None
        return metric_observation(wlan_details_attribute(details, host.get("interface_type")), self._metric)

    @property
    def available(self) -> bool:
        return super().available and self._observation is not None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Use dBm only for the verified Mesh RX signal, not TR-064 values."""
        if self._metric == "signal_strength":
            observation = self._observation
            if observation and observation.get("source_field") == "mesh_rx_rcpi_raw":
                return "dBm"
            return None
        return WLAN_METRICS[self._metric][2]

    @property
    def native_value(self) -> int | float | None:
        observation = self._observation
        return observation["value"] if observation else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        observation = self._observation
        if observation is None:
            return {}
        return {key: value for key, value in observation.items() if key != "value"}


class FritzBoxDeviceCountSensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Expose the number of hosts currently returned by the FRITZ!Box."""

    _attr_has_entity_name = True
    _attr_translation_key = "device_count"
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
                    "dns_name": host.get("dns_name"),
                    "device_type": host.get("device_type"),
                    "device_type_source": host.get("device_type_source"),
                    "device_type_confidence": host.get("device_type_confidence"),
                    "device_manufacturer": host.get("device_manufacturer"),
                    "device_model": host.get("device_model"),
                    "mac_vendor": host.get("mac_vendor"),
                    "mac_vendor_prefix": host.get("mac_vendor_prefix"),
                    "mac_vendor_source": host.get("mac_vendor_source"),
                    "mac_vendor_status": host.get("mac_vendor_status"),
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
    _attr_translation_key = "host_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["online", "offline", "unbekannt", "nicht_gefunden"]
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

        # Suggest a stable, integration-specific entity_id based on the MAC.
        # The visible entity name remains simply "Status" on the device page.
        self.entity_id = f"sensor.fritzbox_network_insight_{compact_mac}_status"

        host = (coordinator.data or {}).get(mac, {})
        device_name = host.get("name") or mac
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=device_name,
            connections={("mac", mac)},
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Use verified identification in the HA device registry."""
        host = self._host or {}
        info = DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            connections={("mac", self._mac)},
            name=str(host.get("name") or self._mac),
        )
        identification = self.coordinator.device_identifications.get(self._mac) or {}
        manufacturer = identification.get("device_manufacturer")
        if not manufacturer and host.get("mac_vendor_status") == "matched":
            manufacturer = host.get("mac_vendor")
        model = identification.get("device_model")
        if manufacturer:
            info["manufacturer"] = manufacturer
        if model:
            info["model"] = model
        return info

    @property
    def _host(self) -> dict[str, Any] | None:
        """Return the latest host record for this MAC."""
        return (self.coordinator.data or {}).get(self._mac)

    @property
    def native_value(self) -> str:
        """Return online, offline, unknown, or not seen in the latest scan."""
        host = self._host
        if host is None:
            return "nicht_gefunden"
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
        attributes: dict[str, Any] = {
            "mac": host["mac"],
            "name": host["name"],
            "ip_address": host["ip_address"],
            "dns_name": host.get("dns_name"),
            "device_type": host.get("device_type"),
            "device_type_source": host.get("device_type_source"),
            "device_type_confidence": host.get("device_type_confidence"),
            "device_manufacturer": host.get("device_manufacturer"),
            "device_model": host.get("device_model"),
            "mac_vendor": host.get("mac_vendor"),
            "mac_vendor_prefix": host.get("mac_vendor_prefix"),
            "mac_vendor_source": host.get("mac_vendor_source"),
            "mac_vendor_status": host.get("mac_vendor_status"),
            "active": host["active"],
            "interface_type": host["interface_type"],
            "seen_in_latest_scan": True,
        }
        # Expose switch-port measurements only for endpoints explicitly
        # identified as Ethernet. FDB reachability alone cannot establish
        # whether a device uses LAN or WLAN.
        details = self.coordinator.device_details.get(self._mac)
        if details is not None:
            lan_ports = [
                dict(observation.value)
                for observation in details.values("lan_switch_port")
                if isinstance(observation.value, dict)
                and observation.value.get("endpoint_access") == "ethernet"
            ]
            if lan_ports:
                attributes["lan_switch_ports"] = lan_ports
            wlan_values = wlan_details_attribute(details, host.get("interface_type"))
            if wlan_values:
                attributes["wlan_details"] = wlan_values
        return attributes


class FritzBoxTopologySensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Expose last observed LLDP links, without implying live connectivity."""

    _attr_has_entity_name = True
    _attr_translation_key = "lldp_topology"
    _attr_icon = "mdi:lan"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_lldp_topology"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FRITZ!Box {entry.data.get('host', '')}",
            manufacturer="AVM",
            model="FRITZ!Box",
        )

    @property
    def native_value(self) -> int:
        """Number of observed LLDP links."""
        return self.coordinator.get_topology_snapshot()["link_count"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the central MAC-keyed topology model."""
        return self.coordinator.get_topology_snapshot()


class FritzBoxFdbTopologySensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Last manually observed MAC reachability via switch ports."""

    _attr_has_entity_name = True
    _attr_translation_key = "fdb_topology"
    _attr_icon = "mdi:lan"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_fdb_topology"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FRITZ!Box {entry.data.get('host', '')}",
            manufacturer="AVM",
            model="FRITZ!Box",
        )

    @property
    def native_value(self) -> int:
        """Total number of saved FDB observations."""
        return self.coordinator.get_fdb_snapshot()["observation_count"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Compact per-port summary; complete entries remain in the store."""
        snapshot = self.coordinator.get_fdb_snapshot()
        by_port: dict[str, dict[str, Any]] = {}
        for item in snapshot["observations"]:
            source = item.get("source_mac") or ""
            port = item.get("interface_name") or item.get("bridge_port") or ""
            key = f"{source}/{port}"
            if key not in by_port:
                by_port[key] = {
                    "source_mac": source,
                    "port": port,
                    "mac_count": 0,
                    "sample_macs": [],
                }
            by_port[key]["mac_count"] += 1
            if len(by_port[key]["sample_macs"]) < 5:
                by_port[key]["sample_macs"].append(item.get("target_mac"))
        return {
            "observation_count": snapshot["observation_count"],
            "source_count": snapshot["source_count"],
            "evidence": snapshot["evidence"],
            "connection": snapshot["connection"],
            "ports": list(by_port.values())[:64],
        }


class FritzBoxCombinedTopologySensor(
    CoordinatorEntity[FritzBoxDataUpdateCoordinator], SensorEntity
):
    """Overview of distinct confirmed LLDP links and FDB port reachability."""

    _attr_has_entity_name = True
    _attr_translation_key = "combined_topology"
    _attr_icon = "mdi:lan"

    def __init__(
        self,
        coordinator: FritzBoxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_combined_topology"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"FRITZ!Box {entry.data.get('host', '')}",
            manufacturer="AVM",
            model="FRITZ!Box",
        )

    @property
    def native_value(self) -> int:
        """Number of MAC-keyed nodes in the combined observation model."""
        return self.coordinator.get_combined_topology_snapshot()["node_count"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Bounded preview; full observations remain in their original stores."""
        snapshot = self.coordinator.get_combined_topology_snapshot()
        return {
            "node_count": snapshot["node_count"],
            "direct_link_count": snapshot["direct_link_count"],
            "reachability_count": snapshot["reachability_count"],
            "lldp_source_count": snapshot["lldp_source_count"],
            "fdb_source_count": snapshot["fdb_source_count"],
            "evidence": snapshot["evidence"],
            "mesh_node_count": snapshot["mesh_node_count"],
            "mesh_link_count": snapshot["mesh_link_count"],
            "mesh_unresolved_link_count": snapshot["mesh_unresolved_link_count"],
            "mesh_links": snapshot["mesh_links"][:32],
            "direct_links": snapshot["direct_links"][:16],
            "reachable_via_port_sample": snapshot["reachable_via_port"][:16],
            "nodes_sample": snapshot["nodes"][:16],
            "samples_truncated": (
                len(snapshot["reachable_via_port"]) > 16
                or len(snapshot["nodes"]) > 16
                or len(snapshot["direct_links"]) > 16
            ),
        }
