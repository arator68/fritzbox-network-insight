"""Explicit, bounded protocol discovery; never called by periodic scans."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from . import DiscoveryAdapter


@dataclass(frozen=True)
class ManualDiscoveryResult:
    """Summary of a user-requested discovery operation."""

    requested: int
    checked: int
    status: str
    protocols: tuple[str, ...] = ()
    details: dict[str, str] | None = None


class ManualDiscoveryRunner:
    """Execute protocol adapters only when the user presses a button."""

    def __init__(self, adapters: tuple[DiscoveryAdapter, ...] = ()) -> None:
        self._adapters = adapters
        self._lock = asyncio.Lock()

    async def async_run(
        self, hosts: dict[str, dict[str, Any]], mac: str | None = None
    ) -> ManualDiscoveryResult:
        """Probe only selected known hosts, with bounded concurrency and time."""
        targets = (
            [hosts[mac]] if mac is not None and mac in hosts
            else list(hosts.values()) if mac is None
            else []
        )
        if not targets:
            return ManualDiscoveryResult(0, 0, "no_targets")
        if not self._adapters:
            return ManualDiscoveryResult(len(targets), 0, "no_adapters_configured")

        async with self._lock:
            semaphore = asyncio.Semaphore(3)

            async def _check(host: dict[str, Any]) -> set[str]:
                found: set[str] = set()
                async with semaphore:
                    for adapter in self._adapters:
                        try:
                            evidence = await asyncio.wait_for(
                                adapter.async_discover(host), timeout=4
                            )
                        except (Exception, TimeoutError):
                            continue
                        if evidence is not None and evidence.protocol:
                            found.add(evidence.protocol)
                return found

            discovered = await asyncio.gather(*(_check(host) for host in targets))
        protocols = tuple(sorted(set().union(*discovered)))
        details: dict[str, str] = {}
        if mac is not None:
            for adapter in self._adapters:
                if adapter.name == "snmp":
                    details = dict(getattr(adapter, "results", {}).get(mac, {}))
        return ManualDiscoveryResult(
            len(targets), len(targets),
            "responded" if protocols else "no_response", protocols, details,
        )
