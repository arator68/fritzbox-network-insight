"""Opt-in SNMPv3 sysInfo discovery for configured known MAC addresses."""
from __future__ import annotations

import asyncio
import ipaddress
from collections.abc import Mapping
from typing import Any

from . import DiscoveryEvidence

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
        mac = str(host.get("mac") or "").upper()
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
            finally:
                engine.close_dispatcher()
            if error_indication or error_status:
                return None
            values = {str(oid): str(value) for oid, value in var_binds}
            if not values:
                return None
            self.results[mac] = {
                "sys_descr": values.get(SYS_DESCR, ""),
                "sys_object_id": values.get(SYS_OBJECT_ID, ""),
                "sys_name": values.get(SYS_NAME, ""),
            }
            return DiscoveryEvidence(source="snmp_v3", protocol="snmp")
        except Exception:
            # No secrets or exception text may enter Home Assistant logs.
            return None
