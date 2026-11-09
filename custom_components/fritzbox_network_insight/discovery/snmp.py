"""Opt-in SNMPv3 sysInfo discovery for configured known MAC addresses."""
from __future__ import annotations

import asyncio
import ipaddress
import json
from collections.abc import Mapping
from typing import Any

from . import DiscoveryEvidence
from .lldp import async_read_lldp
from .fdb import async_read_fdb
from .port_telemetry import async_read_port_telemetry

SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
SYS_NAME = "1.3.6.1.2.1.1.5.0"


class SnmpDiscoveryAdapter:
    """Read SNMPv3 system OIDs; never log or expose secrets."""

    name = "snmp"

    def __init__(self, devices: Mapping[str, Mapping[str, str]]) -> None:
        self._devices = devices
        self.results: dict[str, dict[str, str]] = {}

    async def async_discover(
        self, host: Mapping[str, Any]
    ) -> DiscoveryEvidence | None:
        """Keep all PySNMP MIB loading away from Home Assistant's event loop."""
        return await asyncio.to_thread(self._discover_in_worker, dict(host))

    def _discover_in_worker(
        self, host: Mapping[str, Any]
    ) -> DiscoveryEvidence | None:
        """Run PySNMP asyncio transport on a private worker event loop."""
        return asyncio.run(self._async_discover_worker(host))

    async def _async_discover_worker(
        self, host: Mapping[str, Any]
    ) -> DiscoveryEvidence | None:
        mac = str(host.get("mac") or "").upper()
        self.results.pop(mac, None)
        settings = self._devices.get(mac)
        if not settings:
            return None
        try:
            ip = ipaddress.ip_address(str(host.get("ip_address") or ""))
        except ValueError:
            return None
        if not isinstance(ip, ipaddress.IPv4Address) or not ip.is_private:
            return None
        try:
            # Import only when used: existing integrations still work without SNMP.
            from pysnmp.hlapi.v3arch.asyncio import (
                ContextData, ObjectIdentity, ObjectType, SnmpEngine,
                UdpTransportTarget, UsmUserData, get_cmd,
                usmDESPrivProtocol, usmHMACSHAAuthProtocol,
            )

            user = UsmUserData(
                settings["username"],
                settings["auth_password"],
                settings["priv_password"],
                authProtocol=usmHMACSHAAuthProtocol,
                privProtocol=usmDESPrivProtocol,
            )
            target = await UdpTransportTarget.create(
                (str(ip), 161), timeout=2, retries=0
            )
            # Lazy MIB loading in get_cmd/walk_cmd is also on this worker.
            engine = SnmpEngine()
            try:
                error_indication, error_status, _, var_binds = await asyncio.wait_for(
                    get_cmd(
                        engine, user, target, ContextData(),
                        ObjectType(ObjectIdentity(SYS_DESCR)),
                        ObjectType(ObjectIdentity(SYS_OBJECT_ID)),
                        ObjectType(ObjectIdentity(SYS_NAME)),
                    ),
                    timeout=4,
                )
                if error_indication or error_status:
                    return None
                values = {str(oid): str(value) for oid, value in var_binds}
                if not values:
                    return None
                neighbors, fdb, ports = await asyncio.gather(
                    async_read_lldp(engine, user, target),
                    async_read_fdb(engine, user, target),
                    async_read_port_telemetry(engine, user, target),
                )
            finally:
                engine.close_dispatcher()
            self.results[mac] = {
                "sys_descr": values.get(SYS_DESCR, ""),
                "sys_object_id": values.get(SYS_OBJECT_ID, ""),
                "sys_name": values.get(SYS_NAME, ""),
                "lldp_neighbor_count": str(len(neighbors)),
                "lldp_neighbors": json.dumps(neighbors, ensure_ascii=False),
                "fdb_status": fdb["status"],
                "fdb_source": fdb["source"],
                "fdb_raw_port_count": str(fdb["raw_port_count"]),
                "fdb_raw_status_count": str(fdb["raw_status_count"]),
                "fdb_entry_count": str(fdb["count"]),
                "fdb_truncated": str(fdb["truncated"]).lower(),
                "fdb_entries": json.dumps(fdb["entries"], ensure_ascii=False),
                "port_telemetry_status": ports["status"],
                "port_telemetry_reason": ports.get("reason", ""),
                "port_telemetry_columns": json.dumps(ports.get("columns", {})),
                "port_telemetry_count": str(len(ports["ports"])),
                "port_telemetry": json.dumps(ports["ports"], ensure_ascii=False),
            }
            return DiscoveryEvidence(source="snmp_v3", protocol="snmp")
        except Exception:
            # No secrets or exception text may enter Home Assistant logs.
            return None
