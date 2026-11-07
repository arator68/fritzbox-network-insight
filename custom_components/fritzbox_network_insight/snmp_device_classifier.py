"""Conservative device classification using verified SNMP system information.

SNMP sysObjectID is an enterprise/product identifier, not a device-class
standard. Recognize only explicit, verified model OIDs; never infer a device
class from a vendor prefix, hostname, or generic sysDescr keywords.
"""
from __future__ import annotations

from collections.abc import Mapping

# Verified with the TL-SG3428's live SNMPv3 sysObjectID.
KNOWN_SNMP_MODELS: dict[str, tuple[str, str, str]] = {
    "1.3.6.1.4.1.11863.5.364": ("switch", "TP-Link", "SG3428"),
}


def classify_snmp_system(
    values: Mapping[str, str],
) -> dict[str, str]:
    """Return high-confidence identification for exact known sysObjectIDs."""
    object_id = str(values.get("sys_object_id") or "").strip().lstrip(".")
    known = KNOWN_SNMP_MODELS.get(object_id)
    if known is None:
        return {}

    device_type, manufacturer, model = known
    return {
        "detected_device_type": device_type,
        "detected_device_type_source": "snmp_sys_object_id",
        "device_type_confidence": "high",
        "device_manufacturer": manufacturer,
        "device_model": model,
    }
