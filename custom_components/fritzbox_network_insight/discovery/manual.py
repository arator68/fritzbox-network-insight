"""Explicit, bounded discovery execution; never called by the periodic scan."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from . import DiscoveryAdapter, DiscoveryManager


@dataclass(frozen=True)
class ManualDiscoveryResult:
    """Summary of a user-requested discovery operation."""

    requested: int
    checked: int
    status: str


class ManualDiscoveryRunner:
    """Run optional adapters only after a direct user action."""

    def __init__(self, adapters: tuple[DiscoveryAdapter, ...] = ()) -> None:
        self._adapters = adapters
        self._lock = asyncio.Lock()

    async def async_run(
        self, hosts: dict[str, dict[str, Any]], mac: str | None = None
    ) -> ManualDiscoveryResult:
        """Inspect one MAC or all known hosts without scanning arbitrary IPs."""
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
            manager = DiscoveryManager(self._adapters, active_enabled=True)
            semaphore = asyncio.Semaphore(3)

            async def _check(host: dict[str, Any]) -> None:
                async with semaphore:
                    try:
                        await asyncio.wait_for(manager.async_enrich(host), timeout=8)
                    except TimeoutError:
                        pass

            await asyncio.gather(*(_check(host) for host in targets))
        return ManualDiscoveryResult(len(targets), len(targets), "completed")
