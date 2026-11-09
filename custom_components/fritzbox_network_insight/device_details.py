"""Pure, source-aware detail model for a MAC-identified network device.

This module does not create Home Assistant entities or query devices.
Only observed, usable values are represented; competing sources are retained.
"""
from __future__ import annotations

import json
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
    # X_AVM-DE_Speed is a host-list rate, not a proven LAN port rate.
    # Do not mislabel WLAN host rates as LAN speeds or RX/TX rates.
    if isinstance(raw, Mapping) and "X_AVM-DE_Speed" in raw:
        details.add(
            "tr064_host_speed_mbps", raw["X_AVM-DE_Speed"], source="tr064"
        )
    return details


SNMP_SYSTEM_FIELDS = {
    "sys_descr": "snmp_system_description",
    "sys_object_id": "snmp_system_object_id",
    "sys_name": "snmp_system_name",
}
# These are discovery-result summaries, not current per-port telemetry.
SNMP_SUMMARY_FIELDS = {
    "lldp_neighbor_count": "lldp_neighbor_count",
    "fdb_entry_count": "fdb_entry_count",
    "fdb_raw_port_count": "fdb_raw_port_count",
    "fdb_raw_status_count": "fdb_raw_status_count",
    "fdb_status": "fdb_status",
    "fdb_truncated": "fdb_truncated",
}


def add_snmp_details(
    details: DeviceDetails, discovery: Mapping[str, Any] | None
) -> None:
    """Append actual SNMP discovery values without copying secrets or raw dumps."""
    if not isinstance(discovery, Mapping) or "snmp" not in discovery.get("protocols", ()):
        return
    observed_at = discovery.get("last_run")
    for raw_key, key in {**SNMP_SYSTEM_FIELDS, **SNMP_SUMMARY_FIELDS}.items():
        details.add(
            key, discovery.get(raw_key), source="snmp_v3",
            observed_at=observed_at,
        )


    try:
        fdb_summary = json.loads(discovery.get("fdb_status_summary", "{}"))
    except (TypeError, ValueError):
        fdb_summary = {}
    if isinstance(fdb_summary, dict) and fdb_summary:
        details.add(
            "fdb_status_summary", fdb_summary,
            source="snmp_v3", observed_at=observed_at,
        )

    # Per-port IF-MIB data belongs to the SNMP-managed switch itself.
    # It is not evidence of a direct connection to any learned FDB MAC.
    details.add(
        "snmp_port_telemetry_status",
        discovery.get("port_telemetry_status"),
        source="snmp_v3",
        observed_at=observed_at,
    )
    details.add(
        "snmp_port_telemetry_reason",
        discovery.get("port_telemetry_reason"),
        source="snmp_v3",
        observed_at=observed_at,
    )
    try:
        column_status = json.loads(discovery.get("port_telemetry_columns", "{}"))
    except (TypeError, ValueError):
        column_status = {}
    if isinstance(column_status, dict) and column_status:
        details.add(
            "snmp_port_telemetry_columns", column_status,
            source="snmp_v3", observed_at=observed_at,
        )
    if discovery.get("port_telemetry_status") == "ok":
        try:
            ports = json.loads(discovery.get("port_telemetry", "[]"))
        except (TypeError, ValueError):
            ports = []
        if isinstance(ports, list):
            for port in ports[:128]:
                if not isinstance(port, dict):
                    continue
                if not isinstance(port.get("if_index"), int) or not isinstance(
                    port.get("interface_name"), str
                ):
                    continue
                details.add(
                    "snmp_port_telemetry",
                    {key: port[key] for key in (
                        "if_index", "interface_name", "reported_speed_mbps",
                        "speed_source", "oper_status",
                    ) if key in port},
                    source="snmp_v3_if_mib",
                    observed_at=observed_at,
                )


def add_mesh_link_details(
    details: DeviceDetails, links: list[dict[str, Any]]
) -> None:
    """Retain AVM-reported adjacent links without claiming direct cabling."""
    for link in links:
        if not isinstance(link, dict):
            continue
        if details.mac not in (link.get("source_mac"), link.get("target_mac")):
            continue
        peer = link.get("target_mac") if link.get("source_mac") == details.mac else link.get("source_mac")
        details.add(
            "mesh_reported_link",
            {
                "peer_mac": peer,
                "link_type": link.get("link_type"),
                "link_state": link.get("link_state"),
            },
            source="avm_mesh",
        )


def add_lldp_link_details(
    details: DeviceDetails, observations: Mapping[str, list[dict[str, Any]]]
) -> None:
    """Attach previously observed LLDP neighbors to exact MAC endpoints only."""
    for source_mac, links in observations.items():
        for link in links:
            if not isinstance(link, dict):
                continue
            source = normalize_mac(source_mac)
            target = normalize_mac(link.get("target_mac"))
            if details.mac != source and details.mac != target:
                continue
            peer = target if details.mac == source else source
            details.add(
                "lldp_observed_link",
                {
                    "peer_mac": peer,
                    "local_port": (
                        link.get("source_port_id") if details.mac == source
                        else link.get("target_port_id")
                    ),
                    "match_status": link.get("match_status"),
                },
                source="lldp",
                observed_at=link.get("observed_at"),
            )


def add_wlan_details(
    details: DeviceDetails, observations: Mapping[str, Mapping[str, Any]] | None,
    *, observed_at: str | None = None,
) -> None:
    """Attach only MAC-matched, actually reported WLAN measurements.

    Each WLANConfiguration instance is kept distinct: its number does not
    establish a radio band, and SignalStrength is not assumed to be dBm.
    """
    if not isinstance(observations, Mapping):
        return
    allowed = {
        "wifi_speed_mbps", "wifi_signal_strength", "wifi_channel",
        "wifi_channel_width", "wifi_guest", "wifi_speed_rx_mbps",
        "wifi_speed_max_mbps", "wifi_speed_rx_max_mbps",
        "wifi_frequency_band_mhz",
    }
    # Multiple WLANConfiguration services can return the same association.
    # Retain one copy of each identical measurement rather than three clones.
    seen: set[tuple[str, str]] = set()
    for instance, fields in sorted(observations.items()):
        if not isinstance(fields, Mapping) or not instance.startswith("wlan_configuration_"):
            continue
        for key in sorted(allowed):
            if key not in fields:
                continue
            value = fields[key]
            fingerprint = (key, repr(value))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            details.add(key, value, source=f"tr064_{instance}", observed_at=observed_at)
