"""Offline MAC vendor lookup based on IEEE assignment prefixes.

The bundled starter registry is intentionally small. Unknown prefixes remain
unknown; DNS names are never used as a manufacturer signal.
"""
from __future__ import annotations

import re
from typing import Any

# Selected IEEE assignments from the older Network Map registry.
# Full MA-L/MA-M/MA-S registry migration is a separate follow-up.
_PREFIXES: dict[str, str] = {
    "00040E": "AVM GmbH",
    "00150C": "AVM GmbH",
    "001A4F": "AVM GmbH",
    "001C4A": "AVM GmbH",
    "0024FE": "AVM GmbH",
    "000AEB": "TP-LINK TECHNOLOGIES CO.,LTD.",
    "001478": "TP-LINK TECHNOLOGIES CO.,LTD.",
    "0019E0": "TP-LINK TECHNOLOGIES CO.,LTD.",
    "001D0F": "TP-LINK TECHNOLOGIES CO.,LTD.",
    "002127": "TP-LINK TECHNOLOGIES CO.,LTD.",
    "0023CD": "TP-LINK TECHNOLOGIES CO.,LTD.",
    "F4F50B": "TP-Link Systems Inc.",
    "FCD733": "TP-LINK TECHNOLOGIES CO.,LTD.",
}


def lookup_mac_vendor(mac: Any) -> dict[str, str | None]:
    """Identify the registered MAC-prefix owner, not necessarily device maker."""
    result: dict[str, str | None] = {
        "mac_vendor": None,
        "mac_vendor_prefix": None,
        "mac_vendor_source": None,
        "mac_vendor_status": "unknown",
    }
    normalized = re.sub(r"[^0-9A-Fa-f]", "", str(mac or "")).upper()
    if len(normalized) != 12 or not re.fullmatch(r"[0-9A-F]{12}", normalized):
        result["mac_vendor_status"] = "invalid_mac"
        return result
    first = int(normalized[:2], 16)
    if first & 1:
        result["mac_vendor_status"] = "multicast"
        return result
    if first & 2:
        result["mac_vendor_status"] = "locally_administered"
        return result
    for length in (9, 7, 6):
        prefix = normalized[:length]
        if prefix in _PREFIXES:
            result.update({
                "mac_vendor": _PREFIXES[prefix],
                "mac_vendor_prefix": prefix,
                "mac_vendor_source": "ieee_prefix",
                "mac_vendor_status": "matched",
            })
            break
    return result
