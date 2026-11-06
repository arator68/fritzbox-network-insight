"""Pure device normalization helpers for FRITZ!Box host records."""
from __future__ import annotations

import re
from typing import Any


def normalize_mac(value: Any) -> str | None:
    """Return a normalized MAC address, or None for invalid values."""
    if not isinstance(value, str):
        return None
    compact = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(compact) != 12:
        return None
    return ":".join(compact[index:index + 2] for index in range(0, 12, 2)).upper()


def as_bool(value: Any) -> bool | None:
    """Convert common FRITZ!Box boolean encodings without guessing unknowns."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def normalize_host(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one raw TR-064 host entry into a neutral device model."""
    mac = normalize_mac(raw.get("MACAddress"))
    if mac is None:
        return None
    return {
        "mac": mac,
        "name": str(raw.get("HostName") or raw.get("UserHostName") or "").strip(),
        "ip_address": str(raw.get("IPAddress") or "").strip() or None,
        "interface_type": str(raw.get("InterfaceType") or "").strip() or None,
        "active": as_bool(raw.get("Active")),
        "raw": dict(raw),
    }
