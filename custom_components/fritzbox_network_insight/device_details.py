"""Pure, source-aware detail model for a MAC-identified network device.

This module does not create Home Assistant entities or query devices.
Only observed, usable values are represented; competing sources are retained.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .device import normalize_mac


@dataclass(frozen=True)
class DetailObservation:
    """One source's assertion about a device property."""

    value: Any
    source: str
    observed_at: str | None = None


@dataclass
class DeviceDetails:
    """Device identity and observed properties, independent of HA entities."""

    mac: str
    observations: dict[str, list[DetailObservation]] = field(default_factory=dict)

    def add(
        self,
        key: str,
        value: Any,
        *,
        source: str,
        observed_at: str | None = None,
    ) -> None:
        """Record a usable property without overwriting another source."""
        if not key or not key.strip() or not source or not source.strip():
            raise ValueError("Property key and source are required")
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        self.observations.setdefault(key, []).append(
            DetailObservation(value=value, source=source, observed_at=observed_at)
        )

    def available(self, key: str) -> bool:
        """Whether at least one usable observation exists for this property."""
        return bool(self.observations.get(key))

    def values(self, key: str) -> tuple[DetailObservation, ...]:
        """All assertions for a property, with provenance intact."""
        return tuple(self.observations.get(key, ()))


def build_device_details(
    mac: str,
    observations: Mapping[str, Mapping[str, Any]],
    *,
    observed_at: str | None = None,
) -> DeviceDetails:
    """Combine source-specific property dictionaries without inventing values.

    The caller must supply already-normalized semantic keys; translating
    TR-064, Mesh, SNMP or LLDP fields is a separate adapter responsibility.
    """
    normalized = normalize_mac(mac)
    if normalized is None:
        raise ValueError("A valid MAC address is required")
    details = DeviceDetails(mac=normalized)
    for source, properties in observations.items():
        for key, value in properties.items():
            details.add(key, value, source=source, observed_at=observed_at)
    return details

# Only known semantic fields are promoted to device details. Raw protocol
# payloads remain with their source adapters; no guessed WLAN/port data.
HOST_FIELDS = (
    "name", "ip_address", "dns_name", "active", "interface_type",
    "device_type", "device_type_source", "device_type_confidence",
    "device_manufacturer", "device_model", "mac_vendor",
    "mac_vendor_status", "mesh_role", "mesh_node_uid",
)
TR064_RAW_FIELDS = {
    "HostName": "hostname",
    "UserHostName": "user_hostname",
    "IPAddress": "ipv4_address",
    "InterfaceType": "interface_type",
    "Active": "active",
    "X_AVM-DE_Speed": "lan_speed_mbps",
}


def details_from_host(host: Mapping[str, Any]) -> DeviceDetails:
    """Translate actual host and TR-064 observations into the detail model.

    The raw speed field is retained with explicit TR-064 provenance; it is
    not presented as a verified WLAN link rate or physical switch port.
    """
    mac = normalize_mac(host.get("mac"))
    if mac is None:
        raise ValueError("A valid MAC address is required")
    details = DeviceDetails(mac=mac)
    for key in HOST_FIELDS:
        value = host.get(key)
        if key == "active" and value is not None:
            details.add("online", value, source="tr064")
        elif key in {"mesh_role", "mesh_node_uid"}:
            details.add(key, value, source="avm_mesh")
        elif key in {"device_type", "device_type_source", "device_type_confidence"}:
            details.add(key, value, source="device_classification")
        elif key in {"dns_name"}:
            details.add(key, value, source="dns")
        else:
            details.add(key, value, source="host_registry")
    raw = host.get("raw")
    if isinstance(raw, Mapping):
        for raw_key, semantic_key in TR064_RAW_FIELDS.items():
            if raw_key in raw:
                details.add(semantic_key, raw[raw_key], source="tr064")
    return details
