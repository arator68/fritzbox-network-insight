"""Conservative device classification, independent of discovery protocols.

Names and DNS labels are deliberately not treated as proof of device type.
Manual overrides are keyed by the stable, normalized MAC address.
"""
from __future__ import annotations

from typing import Any

DEVICE_TYPES = frozenset({
    "router", "switch", "access_point", "nas", "printer", "camera",
    "computer", "phone", "tablet", "smart_home", "other",
})


def classify_device(
    host: dict[str, Any],
    overrides: dict[str, dict[str, str]] | None = None,
) -> dict[str, str | None]:
    """Return classification and provenance without guessing from hostnames."""
    mac = str(host.get("mac") or "").upper()
    override = (overrides or {}).get(mac, {})
    kind = str(override.get("device_type") or "").strip().lower()
    if kind in DEVICE_TYPES:
        return {
            "device_type": kind,
            "device_type_source": "manual",
            "device_type_confidence": "confirmed",
        }

    # Only explicit, protocol-provided type declarations are authoritative.
    # FRITZ!Box interface_type (Ethernet/WLAN) is a link type, NOT a device type.
    declared = str(host.get("detected_device_type") or "").strip().lower()
    source = str(host.get("detected_device_type_source") or "").strip()
    if declared in DEVICE_TYPES and source:
        return {
            "device_type": declared,
            "device_type_source": source,
            "device_type_confidence": "detected",
        }

    return {
        "device_type": None,
        "device_type_source": None,
        "device_type_confidence": "unknown",
    }
