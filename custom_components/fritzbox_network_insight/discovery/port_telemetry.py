"""Read-only standard IF-MIB port telemetry, separate from topology inference."""
from __future__ import annotations

from typing import Any

IF_NAME = "1.3.6.1.2.1.31.1.1.1.1"
IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"
IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"

MAX_PORTS = 128
MAX_ROWS = 256
READ_TIMEOUT = 3.0


def parse_port_telemetry(
    names: list[tuple[str, str]],
    high_speeds: list[tuple[str, str]],
    speeds: list[tuple[str, str]],
    statuses: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Return only observed IF-MIB values; no guessed duplex or endpoints."""
    name_map = dict(names)
    high_map = dict(high_speeds)
    speed_map = dict(speeds)
    status_map = dict(statuses)
    ports: list[dict[str, Any]] = []
    for index in sorted(name_map, key=lambda x: (not x.isdecimal(), int(x) if x.isdecimal() else x)):
        if not index.isdecimal() or int(index) <= 0:
            continue
        name = name_map[index][:128]
        if not name:
            continue
        port: dict[str, Any] = {"if_index": int(index), "interface_name": name}
        try:
            high = int(high_map.get(index, ""))
        except ValueError:
            high = 0
        try:
            legacy = int(speed_map.get(index, ""))
        except ValueError:
            legacy = 0
        if high > 0:
            port["reported_speed_mbps"] = high
            port["speed_source"] = "ifHighSpeed"
        elif 0 < legacy < 4294967295:
            port["reported_speed_mbps"] = round(legacy / 1_000_000, 3)
            port["speed_source"] = "ifSpeed"
        status = status_map.get(index)
        if status in {"1", "2", "3", "4", "5", "6", "7"}:
            port["oper_status"] = {
                "1": "up", "2": "down", "3": "testing",
                "4": "unknown", "5": "dormant", "6": "not_present",
                "7": "lower_layer_down",
            }[status]
        ports.append(port)
        if len(ports) >= MAX_PORTS:
            break
    return ports


async def async_read_port_telemetry(engine: Any, user: Any, target: Any) -> dict[str, Any]:
    """Bounded, optional SNMPv3 IF-MIB reads; failures remain explicit."""
    import asyncio
    from pysnmp.hlapi.v3arch.asyncio import ContextData, ObjectIdentity, ObjectType, walk_cmd

    async def walk(base: str) -> list[tuple[str, str]] | None:
        async def read() -> list[tuple[str, str]]:
            rows: list[tuple[str, str]] = []
            async for error, status, _, var_binds in walk_cmd(
                engine, user, target, ContextData(),
                ObjectType(ObjectIdentity(base)), lexicographicMode=False,
            ):
                if error or status:
                    raise RuntimeError("SNMP IF-MIB read failed")
                for oid, value in var_binds:
                    key = str(oid)
                    if not key.startswith(base + "."):
                        return rows
                    rows.append((key[len(base) + 1:], str(value)))
                    if len(rows) >= MAX_ROWS:
                        return rows
            return rows
        try:
            return await asyncio.wait_for(read(), timeout=READ_TIMEOUT)
        except Exception:
            return None

    names, high, speed, status = await asyncio.gather(
        walk(IF_NAME), walk(IF_HIGH_SPEED), walk(IF_SPEED), walk(IF_OPER_STATUS)
    )
    if names is None:
        return {"status": "unavailable", "ports": []}
    return {
        "status": "ok",
        "ports": parse_port_telemetry(names, high or [], speed or [], status or []),
    }
