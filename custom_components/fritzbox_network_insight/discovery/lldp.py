"""Bounded, read-only LLDP-MIB walk through an authenticated SNMPv3 session.

Only actual LLDP advertisements are reported; no inferred topology links.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from time import monotonic
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
WALK_TIMEOUT = 10.0


async def async_read_lldp(
    engine: Any, user: Any, target: Any,
    diagnostics: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Read a small bounded portion of the standard LLDP MIB."""
    from pysnmp.hlapi.v3arch.asyncio import (
        ContextData, ObjectIdentity, ObjectType, walk_cmd,
    )

    started = monotonic()
    phase = "local_ports"
    phase_started = started
    if diagnostics is not None:
        diagnostics.update(status="running", local_ports_status="not_started", remote_status="not_started")

    async def _walk(base: str) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        async for error, status, _, var_binds in walk_cmd(
            engine, user, target, ContextData(),
            ObjectType(ObjectIdentity(base)),
            lexicographicMode=False,
        ):
            if error or status:
                raise RuntimeError("snmp_error")
            for oid, value in var_binds:
                oid_text = str(oid)
                if not oid_text.startswith(base + "."):
                    return rows
                rows.append((oid_text, str(value)))
                if len(rows) >= MAX_ROWS:
                    return rows
        return rows

    async def _read() -> list[dict[str, str]]:
        local_ports: dict[str, str] = {}
        nonlocal phase, phase_started
        for oid, value in await _walk(LOCAL_PORT_ID):
            index = oid[len(LOCAL_PORT_ID) + 1:]
            if index.isdecimal():
                local_ports[index] = value[:128]

        if diagnostics is not None:
            diagnostics["local_ports_status"] = "ok" if local_ports else "empty"
            diagnostics["local_ports_count"] = len(local_ports)
            diagnostics["local_ports_duration_ms"] = round((monotonic() - phase_started) * 1000)
        phase = "remote"
        phase_started = monotonic()
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

        if diagnostics is not None:
            diagnostics["remote_status"] = "ok" if remote else "empty"
            diagnostics["remote_rows_count"] = len(remote)
            diagnostics["remote_duration_ms"] = round((monotonic() - phase_started) * 1000)
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
        neighbors = await asyncio.wait_for(_read(), timeout=WALK_TIMEOUT)
        if diagnostics is not None:
            diagnostics["status"] = "ok" if neighbors else "empty"
        return neighbors
    except TimeoutError:
        if diagnostics is not None:
            diagnostics["status"] = "timeout"
            diagnostics["failed_phase"] = phase
            diagnostics[f"{phase}_status" if phase == "remote" else "local_ports_status"] = "timeout"
        return []
    except Exception:
        if diagnostics is not None:
            diagnostics["status"] = "snmp_error"
            diagnostics["failed_phase"] = phase
            diagnostics[f"{phase}_status" if phase == "remote" else "local_ports_status"] = "snmp_error"
        return []
    finally:
        if diagnostics is not None:
            diagnostics["duration_ms"] = round((monotonic() - started) * 1000)
            if phase == "remote" and "remote_duration_ms" not in diagnostics:
                diagnostics["remote_duration_ms"] = round((monotonic() - phase_started) * 1000)
            elif phase == "local_ports" and "local_ports_duration_ms" not in diagnostics:
                diagnostics["local_ports_duration_ms"] = round((monotonic() - phase_started) * 1000)
