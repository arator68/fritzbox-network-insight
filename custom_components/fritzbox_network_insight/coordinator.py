"""Coordinator for FRITZ!Box Network Insight."""
from __future__ import annotations

import asyncio
import logging
from time import monotonic
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .device_classifier import classify_device
from .discovery import DiscoveryManager
from .mac_vendor import lookup_mac_vendor
from .snmp_device_classifier import classify_snmp_system
from .identification_store import IdentificationStore
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
        self.discovery_results: dict[str | None, dict[str, Any]] = {}
        self.device_identifications: dict[str, dict[str, str]] = {}
        self.identification_store = IdentificationStore(hass, entry.entry_id)
        self._identification_save_lock = asyncio.Lock()
        self._discovery = DiscoveryManager()
        self.entry = entry
        self._dns_cache: dict[str, tuple[float, str | None]] = {}
        self._dns_semaphore = asyncio.Semaphore(4)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def async_load_identifications(self) -> None:
        """Restore verified identifications before the first FRITZ!Box scan."""
        self.device_identifications = await self.identification_store.async_load()

    async def async_record_manual_discovery(
        self, mac: str | None, *, status: str, requested: int, checked: int,
        protocols: tuple[str, ...] = (), details: dict[str, str] | None = None
    ) -> None:
        """Publish a manual result and update verified MAC-based identification."""
        result_details = dict(details or {})
        changed = False
        if mac is not None and "snmp" in protocols:
            identified = classify_snmp_system(result_details)
            if identified:
                if self.device_identifications.get(mac) != identified:
                    self.device_identifications[mac] = identified
                    changed = True
                result_details.update({
                    "device_type": identified["detected_device_type"],
                    "device_type_source": identified["detected_device_type_source"],
                    "device_type_confidence": identified["device_type_confidence"],
                    "device_manufacturer": identified["device_manufacturer"],
                    "device_model": identified["device_model"],
                })
                # Update the live host record so status sensors change immediately.
                if self.data and mac in self.data:
                    host = self.data[mac]
                    host.update(identified)
                    host.update(classify_device(host))
                    host["device_type_confidence"] = identified["device_type_confidence"]

        self.discovery_results[mac] = {
            "status": status,
            "requested": requested,
            "checked": checked,
            "protocols": list(protocols),
            **result_details,
            "last_run": datetime.now(timezone.utc).isoformat(),
        }
        self.async_update_listeners()
        if changed:
            async with self._identification_save_lock:
                try:
                    await self.identification_store.async_save(
                        self.device_identifications
                    )
                except Exception:
                    _LOGGER.exception("Could not persist device identification")

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
        for mac, host in indexed.items():
            indexed[mac] = await self._discovery.async_enrich(host)
        for mac, host in indexed.items():
            identification = self.device_identifications.get(mac)
            if identification:
                host.update(identification)
            host.update(classify_device(host))
            if identification and host.get("device_type_source") == "snmp_sys_object_id":
                host["device_type_confidence"] = identification["device_type_confidence"]
            host.update(lookup_mac_vendor(host.get('mac')))
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
