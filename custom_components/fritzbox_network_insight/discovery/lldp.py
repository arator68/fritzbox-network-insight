"""Bounded, read-only LLDP-MIB walk through an authenticated SNMPv3 session.

Only actual LLDP advertisements are reported; no inferred topology links.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

# LLDP-MIB: remote entry index = timeMark.localPortNum.remoteIndex
REMOTE_BASE = "1.0.8802.1.1.2.1.4.1.1"
LOCAL_PORT_ID = "1.0.8802.1.1.2.1.3.7.1.3"
REMOTE_FIELDS = {
    4: "chassis_id_subtype",
    5: "chassis_id",
    6: "port_id_subtype",
    7: "port_id",
    8: "port_description",
    9: "system_name",
}
MAX_ROWS = 64
MAX_NEIGHBORS = 16
WALK_TIMEOUT = 2.5


async def async_read_lldp_with_status(engine: Any, user: Any, target: Any) -> dict[str, Any]:
    """Read LLDP and report whether the bounded walk completed successfully."""
    from pysnmp.hlapi.v3arch.asyncio import (
        ContextData, ObjectIdentity, ObjectType, walk_cmd,
    )

    async def _walk(base: str) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        async for error, status, _, var_binds in walk_cmd(
            engine, user, target, ContextData(),
            ObjectType(ObjectIdentity(base)),
            lexicographicMode=False,
        ):
            if error or status:
                raise RuntimeError("LLDP walk failed")
            for oid, value in var_binds:
                oid_text = str(oid)
                if not oid_text.startswith(base + "."):
                    return rows
                rows.append((oid_text, str(value)))
                if len(rows) >= MAX_ROWS:
                    raise RuntimeError("LLDP walk truncated")
        return rows

    async def _read() -> list[dict[str, str]]:
        local_ports: dict[str, str] = {}
        for oid, value in await _walk(LOCAL_PORT_ID):
            index = oid[len(LOCAL_PORT_ID) + 1:]
            if index.isdecimal():
                local_ports[index] = value[:128]

        remote: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
        for oid, value in await _walk(REMOTE_BASE):
            suffix = oid[len(REMOTE_BASE) + 1:].split(".")
            if len(suffix) != 4:
                continue
            column, _time_mark, local_port, remote_index = suffix
            if not all(part.isdecimal() for part in suffix):
                continue
            field = REMOTE_FIELDS.get(int(column))
            if field is None:
                continue
            remote[(local_port, remote_index)][field] = value[:256]

        neighbors = []
        for (port, remote_index), fields in sorted(
            remote.items(), key=lambda item: (int(item[0][0]), int(item[0][1]))
        )[:MAX_NEIGHBORS]:
            if not fields:
                continue
            neighbors.append({
                "local_port_number": port,
                "local_port_id": local_ports.get(port, ""),
                "remote_index": remote_index,
                **fields,
            })
        return neighbors

    try:
        return {"status": "ok", "neighbors": await asyncio.wait_for(_read(), timeout=WALK_TIMEOUT)}
    except Exception:
        # A failed read is not an empty neighbor table.
        return {"status": "failed", "neighbors": []}


async def async_read_lldp(engine: Any, user: Any, target: Any) -> list[dict[str, str]]:
    """Backward-compatible reader for existing callers."""
    return (await async_read_lldp_with_status(engine, user, target))["neighbors"]
