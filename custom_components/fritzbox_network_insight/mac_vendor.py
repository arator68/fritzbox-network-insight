"""Offline IEEE MAC assignment lookup.

Supports MA-L (24-bit), MA-M (28-bit) and MA-S (36-bit) prefixes.
The optional mac_vendors.csv is packaged alongside this module.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
import re
from typing import Any

_DATABASE = Path(__file__).with_name("mac_vendors.csv")
_MAC_RE = re.compile(r"^[0-9A-F]{12}$")


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, str]:
    """Read the bundled vendor database once per integration process."""
    entries: dict[str, str] = {}
    try:
        with _DATABASE.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                prefix = re.sub(
                    r"[^0-9A-Fa-f]", "", str(row.get("prefix") or row.get("Assignment") or "")
                ).upper()
                vendor = str(row.get("vendor") or row.get("Organization Name") or "").strip()
                if len(prefix) in (6, 7, 9) and vendor and re.fullmatch(r"[0-9A-F]+", prefix):
                    entries[prefix] = vendor
    except (OSError, UnicodeError, csv.Error):
        return {}
    return entries


def lookup_mac_vendor(mac: Any) -> dict[str, str | None]:
    """Return registered prefix owner, never a guessed device manufacturer."""
    result: dict[str, str | None] = {
        "mac_vendor": None,
        "mac_vendor_prefix": None,
        "mac_vendor_source": None,
        "mac_vendor_status": "unknown",
    }
    normalized = re.sub(r"[^0-9A-Fa-f]", "", str(mac or "")).upper()
    if not _MAC_RE.fullmatch(normalized):
        result["mac_vendor_status"] = "invalid_mac"
        return result
    first = int(normalized[:2], 16)
    if first & 1:
        result["mac_vendor_status"] = "multicast"
        return result
    if first & 2:
        result["mac_vendor_status"] = "locally_administered"
        return result
    entries = _load_registry()
    if not entries:
        result["mac_vendor_status"] = "database_unavailable"
        return result
    for length in (9, 7, 6):
        prefix = normalized[:length]
        if prefix in entries:
            result.update({
                "mac_vendor": entries[prefix],
                "mac_vendor_prefix": prefix,
                "mac_vendor_source": "ieee_prefix",
                "mac_vendor_status": "matched",
            })
            break
    return result
