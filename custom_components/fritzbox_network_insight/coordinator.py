"""Coordinator for FRITZ!Box Network Insight."""
from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .dns import resolve_dns_name
from .fritzbox_client import (
    FritzBoxAuthenticationError,
    FritzBoxClient,
    FritzBoxConnectionError,
)

_LOGGER = logging.getLogger(__name__)


class FritzBoxDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch and normalize the current FRITZ!Box host list."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FritzBoxClient,
        entry: ConfigEntry,
    ) -> None:
        self.client = client
        self.entry = entry
        self._dns_cache: dict[str, tuple[float, str | None]] = {}
        self._dns_semaphore = asyncio.Semaphore(4)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch hosts in the executor and index them by stable MAC address."""
        try:
            hosts = await self.hass.async_add_executor_job(self.client.get_hosts)
        except FritzBoxAuthenticationError as err:
            _LOGGER.error("Authentication with the configured FRITZ!Box was rejected")
            raise ConfigEntryAuthFailed(
                "FRITZ!Box authentication failed; check the configured credentials"
            ) from err
        except FritzBoxConnectionError as err:
            _LOGGER.warning("Could not retrieve the FRITZ!Box host list: %s", err)
            raise UpdateFailed("Could not retrieve the FRITZ!Box host list") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error while retrieving FRITZ!Box hosts")
            raise UpdateFailed("Unexpected error while retrieving FRITZ!Box hosts") from err

        indexed = {host["mac"]: host for host in hosts}
        # DNS is optional metadata: lookup failures never fail the FRITZ!Box scan.
        # Cache positive and negative results for 15 minutes per IP address.
        addresses = {
            host["ip_address"]
            for host in hosts
            if host.get("ip_address")
        }
        now = monotonic()
        expired = [
            ip for ip, (expiry, _) in self._dns_cache.items()
            if expiry <= now
        ]
        for ip in expired:
            del self._dns_cache[ip]

        async def _resolve(ip: str) -> None:
            if ip in self._dns_cache:
                return
            async with self._dns_semaphore:
                try:
                    name = await self.hass.async_add_executor_job(
                        resolve_dns_name, ip
                    )
                except Exception:
                    _LOGGER.debug("DNS lookup failed for %s", ip, exc_info=True)
                    name = None
                self._dns_cache[ip] = (monotonic() + 900, name)

        try:
            await asyncio.wait_for(
                asyncio.gather(*(_resolve(ip) for ip in addresses)), timeout=8
            )
        except TimeoutError:
            _LOGGER.debug("DNS enrichment timed out; continuing host scan")
        for host in indexed.values():
            ip = host.get("ip_address")
            host["dns_name"] = (
                self._dns_cache[ip][1]
                if ip and ip in self._dns_cache
                else None
            )
        _LOGGER.info("FRITZ!Box host scan completed: %d device(s) found", len(indexed))
        for host in indexed.values():
            _LOGGER.debug(
                "FRITZ!Box device: MAC=%s name=%r IP=%s active=%s interface=%s",
                host["mac"],
                host["name"],
                host["ip_address"],
                host["active"],
                host["interface_type"],
            )
        return indexed
