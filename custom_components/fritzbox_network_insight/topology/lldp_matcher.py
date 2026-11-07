"""Conservative LLDP chassis MAC matching against FRITZ!Box host records.

Only an exact chassis MAC match is sufficient. No hostname, OUI, IP, or
similarity guesses. Unmatched neighbors remain visible and unidentified.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_MAC = re.compile(r"^[0-9A-F]{12}$")


def normalize_mac(value: Any) -> str | None:
    """Normalize common human-readable MAC representations."""
    if not isinstance(value, str):
        return None
    compact = value.strip().replace(":", "").replace("-", "").replace(".", "").upper()
    if not _MAC.fullmatch(compact):
        return None
    return ":".join(compact[i:i + 2] for i in range(0, 12, 2))


def match_lldp_neighbors(
    neighbors: list[dict[str, Any]],
    hosts: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Annotate LLDP observations without manufacturing topology links."""
    by_mac: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
    for key, host in hosts.items():
        mac = normalize_mac(host.get("mac") or key)
        if mac:
            by_mac.setdefault(mac, []).append((key, host))

    results: list[dict[str, Any]] = []
    for neighbor in neighbors:
        item = dict(neighbor)
        # LLDP chassis ID subtype 4 = MAC address. Other types cannot be
        # treated as MACs even if their textual representation looks similar.
        subtype = str(item.get("chassis_id_subtype", ""))
        chassis_mac = normalize_mac(item.get("chassis_id")) if subtype == "4" else None
        item["chassis_mac"] = chassis_mac
        item["match_status"] = "unmatched"
        item["match_method"] = "exact_chassis_mac" if chassis_mac else "none"
        if chassis_mac:
            matches = by_mac.get(chassis_mac, [])
            if len(matches) == 1:
                key, host = matches[0]
                item["match_status"] = "matched"
                item["matched_mac"] = normalize_mac(host.get("mac") or key)
                item["matched_name"] = str(host.get("name") or "")
                item["matched_ip_address"] = str(host.get("ip_address") or "")
            elif len(matches) > 1:
                item["match_status"] = "ambiguous"
        results.append(item)
    return results
