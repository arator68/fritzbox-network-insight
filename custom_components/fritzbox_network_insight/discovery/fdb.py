"""Read-only, bounded BRIDGE-MIB forwarding database observations.

A learned MAC is reachable via a bridge port; it is NOT necessarily directly
attached. This module intentionally creates no topology edges.
"""
from __future__ import annotations

import asyncio
from typing import Any

FDB_PORT = "1.3.6.1.2.1.17.4.3.1.2"
FDB_STATUS = "1.3.6.1.2.1.17.4.3.1.3"
BRIDGE_PORT_IFINDEX = "1.3.6.1.2.1.17.1.4.1.2"
IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
MAX_ROWS = 512
MAX_RESULTS = 128
READ_TIMEOUT = 3.0


def mac_from_oid_suffix(suffix: str) -> str | None:
    """FDB indices are six decimal octets, not textual MAC values."""
    parts = suffix.split(".")
    if len(parts) != 6 or not all(part.isdecimal() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    if any(part > 255 for part in numbers):
        return None
    return ":".join(f"{part:02X}" for part in numbers)


def correlate_fdb(
    port_rows: list[tuple[str, str]],
    status_rows: list[tuple[str, str]],
    bridge_rows: list[tuple[str, str]],
    name_rows: list[tuple[str, str]],
) -> list[dict[str, str]]:
    """Map dynamic learned MACs to bridge ports and optional interfaces."""
    statuses = dict(status_rows)
    bridge = dict(bridge_rows)
    names = dict(name_rows)
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for suffix, bridge_port in port_rows:
        mac = mac_from_oid_suffix(suffix)
        if mac is None or mac in seen or not bridge_port.isdecimal():
            continue
        # dot1dTpFdbStatus: 3 = learned. Exclude self/static/invalid.
        if statuses.get(suffix) != "3":
            continue
        seen.add(mac)
        if_index = bridge.get(bridge_port, "")
        results.append({
            "mac": mac,
            "bridge_port": bridge_port,
            "if_index": if_index,
            "interface_name": names.get(if_index, "")[:128],
            "evidence": "bridge_mib_dynamic_fdb",
            "connection": "reachable_via_port",
        })
        if len(results) >= MAX_RESULTS:
            break
    return results


async def async_read_fdb(engine: Any, user: Any, target: Any) -> dict[str, Any]:
    """Walk standard MIBs with strict bounds; failures are not empty success."""
    from pysnmp.hlapi.v3arch.asyncio import (
        ContextData, ObjectIdentity, ObjectType, walk_cmd,
    )

    async def _walk(base: str) -> list[tuple[str, str]]:
        async def _read() -> list[tuple[str, str]]:
            rows: list[tuple[str, str]] = []
            async for error, status, _, var_binds in walk_cmd(
                engine, user, target, ContextData(),
                ObjectType(ObjectIdentity(base)),
                lexicographicMode=False,
            ):
                if error or status:
                    raise RuntimeError("SNMP walk failed")
                for oid, value in var_binds:
                    text = str(oid)
                    if not text.startswith(base + "."):
                        return rows
                    rows.append((text[len(base) + 1:], str(value)))
                    if len(rows) >= MAX_ROWS:
                        return rows
            return rows
        return await asyncio.wait_for(_read(), timeout=READ_TIMEOUT)

    try:
        ports, statuses, bridge, names = await asyncio.gather(
            _walk(FDB_PORT), _walk(FDB_STATUS),
            _walk(BRIDGE_PORT_IFINDEX), _walk(IF_NAME),
        )
        observations = correlate_fdb(ports, statuses, bridge, names)
        return {"status": "ok", "entries": observations, "count": len(observations),
                "truncated": len(ports) >= MAX_ROWS or len(observations) >= MAX_RESULTS}
    except Exception:
        return {"status": "unavailable", "entries": [], "count": 0, "truncated": False}
