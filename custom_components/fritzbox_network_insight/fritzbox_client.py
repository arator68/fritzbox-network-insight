"""Synchronous FRITZ!Box TR-064 adapter.

Blocking library calls must only be invoked from Home Assistant's executor.
"""
from __future__ import annotations

from typing import Any

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import (
    FritzAuthorizationError,
    FritzConnectionException,
    FritzSecurityError,
)
from fritzconnection.lib.fritzhosts import FritzHosts

from .device import normalize_host


class FritzBoxAuthenticationError(Exception):
    """The FRITZ!Box rejected the supplied credentials."""


class FritzBoxConnectionError(Exception):
    """The FRITZ!Box could not be reached or queried."""


class FritzBoxClient:
    """Read the FRITZ!Box host list through the TR-064 host service."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        timeout: int = 10,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout

    def get_hosts(self) -> list[dict[str, Any]]:
        """Connect and return normalized hosts."""
        try:
            connection = FritzConnection(
                address=self.host,
                user=self.username,
                password=self.password,
                timeout=self.timeout,
            )
            raw_hosts = FritzHosts(connection).get_hosts_attributes()
        except (FritzAuthorizationError, FritzSecurityError) as err:
            raise FritzBoxAuthenticationError from err
        except (FritzConnectionException, OSError, TimeoutError) as err:
            raise FritzBoxConnectionError from err

        unique: dict[str, dict[str, Any]] = {}
        for raw in raw_hosts:
            host = normalize_host(raw)
            if host is not None:
                # MAC address is the stable identity; retain the first record.
                unique.setdefault(host["mac"], host)
        return sorted(unique.values(), key=lambda item: item["mac"])
