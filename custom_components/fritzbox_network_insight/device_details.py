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
