"""Read-only, bounded diagnostic representation of observed device details."""
from __future__ import annotations

from typing import Mapping

from .device import normalize_mac
from .device_details import DeviceDetails


def device_details_snapshot(
    devices: Mapping[str, DeviceDetails], mac: str | None = None
) -> dict:
    """Return JSON-safe observations, with source and observation timestamp."""
    selected = normalize_mac(mac) if mac is not None else None
    if mac is not None and selected is None:
        return {"error": "Invalid MAC address"}
    if selected is not None and selected not in devices:
        return {"error": "Device MAC not found in current scan"}
    chosen = [selected] if selected else sorted(devices)
    result = {}
    for key in chosen:
        details = devices[key]
        result[key] = {
            property_name: [
                {"value": observation.value, "source": observation.source,
                 "observed_at": observation.observed_at}
                for observation in observations
            ]
            for property_name, observations in sorted(details.observations.items())
        }
    return {"device_count": len(result), "devices": result}
