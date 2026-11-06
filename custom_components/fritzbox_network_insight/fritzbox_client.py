"""Small synchronous adapter for FRITZ!Box TR-064 host discovery.

All blocking fritzconnection calls must be executed in Home Assistant's
executor by the caller.
"""
from __future__ import annotations

import re
from typing import Any

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
)
from fritzconnection.lib.fritzhosts import FritzHosts


class FritzBoxAuthenticationError(Exception):
    """The FRITZ!Box rejected the supplied credentials."""


class FritzBoxConnectionError(Exception):
    """The FRITZ!Box could not be reached or queried."""


def normalize_mac(value: Any) -> str | None:
    """Return a normalized MAC address, or None for invalid values."""
    if not isinstance(value, str):
        return None
    compact = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(compact) != 12:
        return None
    return ":".join(compact[index:index + 2] for index in range(0, 12, 2)).upper()


def normalize_host(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Convert one raw TR-064 host entry into the integration's neutral model."""
    mac = normalize_mac(raw.get("MACAddress"))
    if mac is None:
        return None

    return {
        "mac": mac,
        "name": str(raw.get("HostName") or raw.get("UserHostName") or "").strip(),
        "ip_address": str(raw.get("IPAddress") or "").strip() or None,
        "interface_type": str(raw.get("InterfaceType") or "").strip() or None,
        "active": _as_bool(raw.get("Active")),
        "raw": dict(raw),
    }


def _as_bool(value: Any) -> bool | None:
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


class FritzBoxClient:
    """Access the FRITZ!Box host list through the TR-064 host service."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        use_tls: bool = False,
        timeout: int = 10,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout

    def get_hosts(self) -> list[dict[str, Any]]:
        """Connect and return normalized hosts; raises typed connection errors."""
        try:
            connection = FritzConnection(
                address=self.host,
                user=self.username,
                password=self.password,
                use_tls=self.use_tls,
                timeout=self.timeout,
            )
            raw_hosts = FritzHosts(connection).get_hosts_attributes()
        except (FritzAuthorizationError, FritzSecurityError) as err:
            raise FritzBoxAuthenticationError from err
        except FritzConnectionException as err:
            raise FritzBoxConnectionError from err
        except (OSError, TimeoutError) as err:
            raise FritzBoxConnectionError from err

        hosts = [host for raw in raw_hosts if (host := normalize_host(raw))]
        # MAC is the stable identity. Duplicate records are collapsed without
        # allowing a later duplicate to silently replace the first observation.
        unique: dict[str, dict[str, Any]] = {}
        for host in hosts:
            unique.setdefault(host["mac"], host)
        return sorted(unique.values(), key=lambda item: item["mac"])
