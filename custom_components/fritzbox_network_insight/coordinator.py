"""Coordinator for FRITZ!Box Network Insight."""
from __future__ import annotations

import asyncio
import logging
import json
from time import monotonic
from datetime import datetime, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import device_registry as dr

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .device_classifier import classify_device
from .discovery import DiscoveryManager
from .discovery.snmp import SnmpDiscoveryAdapter
from .mac_vendor import lookup_mac_vendor
from .mesh import fetch_mesh, parse_mesh
from .mesh_wlan_details import extract_mesh_wlan_details
from .wlan_details import fetch_wlan_devices
from .device_details import (
    DeviceDetails, details_from_host, add_snmp_details,
    add_mesh_link_details, add_lldp_link_details, add_wlan_details,
)
from .lan_device_details import add_lan_port_details
from .snmp_device_classifier import classify_snmp_system
from .identification_store import IdentificationStore
from .topology.lldp_matcher import match_lldp_neighbors
from .topology.model import build_lldp_links, topology_snapshot
from .topology.store import TopologyStore
from .topology.fdb_model import build_fdb_observations
from .topology.fdb_store import FdbTopologyStore
from .topology.combined import build_combined_topology
from .topology.internal_graph import build_internal_graph
from .topology.manual_store import ManualTopologyStore, sanitize_links
from .topology.port_history import PortHistoryStore, merge_port_history
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
        self.device_details: dict[str, DeviceDetails] = {}
        self.identification_store = IdentificationStore(hass, entry.entry_id)
        self.topology_store = TopologyStore(hass, entry.entry_id)
        self.fdb_topology_store = FdbTopologyStore(hass, entry.entry_id)
        self.manual_topology_store = ManualTopologyStore(hass, entry.entry_id)
        self.port_history_store = PortHistoryStore(hass, entry.entry_id)
        self.port_history: list[dict[str, str]] = []
        self.manual_links: list[dict[str, str]] = []
        self._manual_links_lock = asyncio.Lock()
        self.fdb_observations: dict[str, list[dict[str, str | None]]] = {}
        self.topology_observations: dict[str, list[dict[str, Any]]] = {}
        self._topology_save_lock = asyncio.Lock()
        self._identification_save_lock = asyncio.Lock()
        self._discovery = DiscoveryManager()
        self.entry = entry
        self.mesh_topology: dict[str, Any] = {"nodes": [], "links": [], "aliases": {}}
        self._mesh_last_attempt: float = 0.0
        self._mesh_wlan_details: dict[str, list[dict[str, Any]]] = {}
        self._mesh_wlan_observed_at: str | None = None
        self._wlan_observations: dict[str, dict[str, dict[str, Any]]] = {}
        self._wlan_observed_at: str | None = None
        self._wlan_last_attempt: float = 0.0
        self._snmp_last_attempt: float = 0.0
        self._snmp_scan_lock = asyncio.Lock()
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
        for mac, identification in self.device_identifications.items():
            self._update_identified_device_registry(mac, identification)

    async def async_load_topology(self) -> None:
        """Restore last-observed LLDP links; not a live connectivity claim."""
        try:
            self.topology_observations = await self.topology_store.async_load()
        except Exception:
            _LOGGER.exception("Could not load saved LLDP topology")
            self.topology_observations = {}

    async def async_load_fdb_topology(self) -> None:
        """Restore last manual FDB observations, not live connectivity."""
        try:
            self.fdb_observations = await self.fdb_topology_store.async_load()
        except Exception:
            _LOGGER.exception("Could not load saved FDB topology")
            self.fdb_observations = {}

    async def async_load_port_history(self) -> None:
        """Restore last-seen port records without claiming devices are online."""
        try:
            self.port_history = await self.port_history_store.async_load()
        except Exception:
            _LOGGER.exception("Could not load saved port history")
            self.port_history = []

    async def async_load_manual_links(self) -> None:
        """Restore explicitly confirmed physical connections."""
        self.manual_links = await self.manual_topology_store.async_load()

    async def async_set_manual_link(
        self, source_mac: str, target_mac: str, *,
        bridge_port: str = "", vlan_id: str = "",
    ) -> list[dict[str, str]]:
        """Persist an explicit physical confirmation, atomically per entry."""
        candidate = sanitize_links([{
            "source_mac": source_mac, "target_mac": target_mac,
            "bridge_port": bridge_port, "vlan_id": vlan_id,
            "confirmation": "user_confirmed",
        }])
        if not candidate:
            raise ValueError("Invalid manual link")
        link = candidate[0]
        async with self._manual_links_lock:
            new_links = [
                old for old in self.manual_links
                if frozenset((old["source_mac"], old["target_mac"]))
                != frozenset((link["source_mac"], link["target_mac"]))
            ] + [link]
            if len(new_links) > 128:
                raise ValueError("Too many manually confirmed links")
            await self.manual_topology_store.async_save(new_links)
            self.manual_links = new_links
        return list(self.manual_links)

    async def async_delete_manual_link(
        self, source_mac: str, target_mac: str
    ) -> list[dict[str, str]]:
        """Remove one confirmation by its stable MAC pair."""
        from .topology.lldp_matcher import normalize_mac
        source, target = normalize_mac(source_mac), normalize_mac(target_mac)
        if not source or not target or source == target:
            raise ValueError("Invalid MAC pair")
        async with self._manual_links_lock:
            new_links = [
                old for old in self.manual_links
                if frozenset((old["source_mac"], old["target_mac"]))
                != frozenset((source, target))
            ]
            await self.manual_topology_store.async_save(new_links)
            self.manual_links = new_links
        return list(self.manual_links)

    def get_fdb_snapshot(self) -> dict[str, Any]:
        """Expose last-observed MAC reachability separately from LLDP links."""
        observations = [
            dict(item)
            for source in sorted(self.fdb_observations)
            for item in self.fdb_observations[source]
        ]
        return {
            "observations": observations,
            "observation_count": len(observations),
            "source_count": len(self.fdb_observations),
            "evidence": "last_manual_fdb_observation",
            "connection": "reachable_via_port",
        }

    def get_combined_topology_snapshot(self) -> dict[str, Any]:
        """Combine persisted LLDP and FDB evidence without inferring links."""
        return build_combined_topology(
            self.topology_observations,
            self.fdb_observations,
            self.data or {},
            self.mesh_topology,
        )

    def get_internal_topology_graph(self) -> dict[str, Any]:
        """Build the full internal graph without exposing it as sensor attributes."""
        snapshot = self.get_combined_topology_snapshot()
        snapshot["manual_links"] = list(self.manual_links)
        snapshot["port_history"] = list(self.port_history)
        return build_internal_graph(snapshot)

    def get_topology_snapshot(self) -> dict[str, Any]:
        """Provide a single, dashboard-ready topology data model."""
        return topology_snapshot(self.topology_observations, self.data or {})

    def _update_identified_device_registry(
        self, mac: str, identification: dict[str, str]
    ) -> None:
        """Update an existing HA device after verified SNMP identification."""
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={(DOMAIN, mac)})
        if device is None:
            return
        changes: dict[str, str] = {}
        manufacturer = identification.get("device_manufacturer")
        model = identification.get("device_model")
        if manufacturer and device.manufacturer != manufacturer:
            changes["manufacturer"] = manufacturer
        if model and device.model != model:
            changes["model"] = model
        if changes:
            registry.async_update_device(device.id, **changes)

    async def async_record_manual_discovery(
        self, mac: str | None, *, status: str, requested: int, checked: int,
        protocols: tuple[str, ...] = (), details: dict[str, str] | None = None
    ) -> None:
        """Publish a manual result and update verified MAC-based identification."""
        result_details = dict(details or {})
        # Match only exact LLDP chassis MACs against known FRITZ!Box hosts.
        # This is an observation annotation, not an inferred network edge.
        if mac is not None and "lldp_neighbors" in result_details:
            try:
                raw_neighbors = json.loads(result_details["lldp_neighbors"])
                if isinstance(raw_neighbors, list) and all(
                    isinstance(item, dict) for item in raw_neighbors
                ):
                    matched = match_lldp_neighbors(raw_neighbors, self.data or {})
                    result_details["lldp_neighbors"] = json.dumps(
                        matched, ensure_ascii=False
                    )
                    result_details["lldp_matched_count"] = str(sum(
                        item["match_status"] == "matched" for item in matched
                    ))
                    result_details["lldp_unmatched_count"] = str(sum(
                        item["match_status"] == "unmatched" for item in matched
                    ))
                    result_details["lldp_ambiguous_count"] = str(sum(
                        item["match_status"] == "ambiguous" for item in matched
                    ))
            except (ValueError, TypeError):
                _LOGGER.debug("Could not parse LLDP neighbor observations")
        topology_changed = False
        if mac is not None and "snmp" in protocols and "lldp_neighbors" in result_details:
            try:
                parsed = json.loads(result_details["lldp_neighbors"])
                if isinstance(parsed, list) and all(isinstance(n, dict) for n in parsed):
                    links = build_lldp_links(mac, parsed)
                    if mac in self.topology_observations or links:
                        self.topology_observations[mac] = links
                        topology_changed = True
            except (ValueError, TypeError):
                _LOGGER.debug("Invalid LLDP observations; retaining previous topology")
        fdb_changed = False
        # Only replace saved FDB observations after a successful complete walk.
        # Unavailable or truncated results must preserve the previous snapshot.
        if (mac is not None and "snmp" in protocols
                and result_details.get("fdb_status") == "ok"
                and result_details.get("fdb_truncated") == "false"
                and "fdb_entries" in result_details):
            try:
                entries = json.loads(result_details["fdb_entries"])
                if isinstance(entries, list) and all(isinstance(item, dict) for item in entries):
                    observations = build_fdb_observations(mac, entries, self.data or {})
                    self.fdb_observations[mac] = observations
                    fdb_changed = True
            except (ValueError, TypeError):
                _LOGGER.debug("Invalid FDB observations; retaining previous topology")

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
                self._update_identified_device_registry(mac, identified)
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
        # Manual SNMP discovery runs independently of the periodic host scan.
        # Refresh derived port evidence immediately from the new observations.
        # The next host scan will rebuild the same evidence from scratch.
        if self.device_details and mac is not None:
            add_lan_port_details(
                self.device_details, self.discovery_results, self.fdb_observations
            )
        self.async_update_listeners()
        if fdb_changed:
            async with self._topology_save_lock:
                try:
                    # A complete SNMP FDB walk is evidence of observation,
                    # not proof of a direct cable or current online status.
                    updated = merge_port_history(
                        self.port_history, self.fdb_observations.get(mac, [])
                    )
                    await self.port_history_store.async_save(updated)
                    self.port_history = updated
                except Exception:
                    _LOGGER.exception("Could not persist port history")
        if fdb_changed:
            async with self._topology_save_lock:
                try:
                    await self.fdb_topology_store.async_save(self.fdb_observations)
                except Exception:
                    _LOGGER.exception("Could not persist FDB topology")
        if topology_changed:
            async with self._topology_save_lock:
                try:
                    await self.topology_store.async_save(self.topology_observations)
                except Exception:
                    _LOGGER.exception("Could not persist LLDP topology")
        if changed:
            async with self._identification_save_lock:
                try:
                    await self.identification_store.async_save(
                        self.device_identifications
                    )
                except Exception:
                    _LOGGER.exception("Could not persist device identification")

    async def _async_refresh_snmp_topology(self, hosts: dict[str, dict[str, Any]]) -> None:
        """Periodically refresh configured switches; never invent physical links.

        Failed or incomplete walks preserve the last saved observations. The
        configured SNMPv3 credentials are never logged or copied to diagnostics.
        """
        configured = self.entry.options.get("snmp_devices", {})
        if not isinstance(configured, dict) or not configured:
            return
        now = monotonic()
        if self._snmp_last_attempt and now - self._snmp_last_attempt < 300:
            return
        if self._snmp_scan_lock.locked():
            return
        async with self._snmp_scan_lock:
            self._snmp_last_attempt = monotonic()
            adapter = SnmpDiscoveryAdapter(configured)
            for mac in sorted(configured):
                host = hosts.get(mac)
                if not host:
                    continue
                try:
                    evidence = await asyncio.wait_for(adapter.async_discover(host), timeout=15)
                    if evidence is None:
                        continue
                    details = adapter.results.get(mac, {})
                    if details.get("fdb_status") != "ok" or details.get("fdb_truncated") != "false":
                        continue
                    await self.async_record_manual_discovery(
                        mac, status="responded", requested=1, checked=1,
                        protocols=("snmp",), details=details,
                    )
                except Exception:
                    _LOGGER.warning("Automatic SNMP topology refresh failed for %s", mac)

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
        # WLAN observations are optional, throttled and never fail the host scan.
        now_wlan = monotonic()
        if not self._wlan_last_attempt or now_wlan - self._wlan_last_attempt >= 300:
            self._wlan_last_attempt = now_wlan
            try:
                wlan = await self.hass.async_add_executor_job(
                    fetch_wlan_devices, self.client.host, self.client.username,
                    self.client.password, self.client.timeout,
                )
                self._wlan_observations = wlan
                self._wlan_observed_at = datetime.now(timezone.utc).isoformat()
            except Exception:
                _LOGGER.debug("Optional WLAN device list unavailable", exc_info=True)
        await self._async_refresh_snmp_topology(indexed)
        # Mesh refresh every 15 minutes; keep the last successful result.
        now_mesh = monotonic()
        if not self._mesh_last_attempt or now_mesh - self._mesh_last_attempt >= 900:
            self._mesh_last_attempt = now_mesh
            try:
                payload = await self.hass.async_add_executor_job(
                    fetch_mesh, self.client.host, self.client.username,
                    self.client.password, self.client.timeout,
                )
                parsed_mesh = parse_mesh(payload, indexed)
                self._mesh_wlan_details = extract_mesh_wlan_details(
                    payload, parsed_mesh.get("aliases", {})
                )
                self.mesh_topology = parsed_mesh
                self._mesh_wlan_observed_at = datetime.now(timezone.utc).isoformat()
            except Exception as err:
                _LOGGER.warning("AVM Mesh refresh failed; retaining previous data: %s", err)
        mesh_nodes = {node["mac"]: node for node in self.mesh_topology.get("nodes", [])}
        for mac, host in indexed.items():
            canonical = self.mesh_topology.get("aliases", {}).get(mac, mac)
            node = mesh_nodes.get(canonical)
            if node:
                host["mesh_role"] = node.get("mesh_role")
                host["mesh_node_uid"] = node.get("uid")
                host["mesh_identity_mac"] = canonical
                if str(node.get("mesh_role") or "").lower() == "slave":
                    host["device_manufacturer"] = "AVM"

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
        # Publish only successfully assembled detail snapshots after enrichment.
        # These are internal observations; entity creation is intentionally separate.
        self.device_details = {
            mac: details_from_host(host) for mac, host in indexed.items()
        }
        for mac, details in self.device_details.items():
            add_snmp_details(details, self.discovery_results.get(mac))
            add_mesh_link_details(details, self.mesh_topology.get("links", []))
            add_lldp_link_details(details, self.topology_observations)
            add_wlan_details(
                details, self._wlan_observations.get(mac),
                observed_at=self._wlan_observed_at,
            )
            for radio in self._mesh_wlan_details.get(mac, []):
                for key, value in radio.items():
                    details.add(
                        key, value, source="avm_mesh_radio",
                        observed_at=self._mesh_wlan_observed_at,
                    )
        add_lan_port_details(
            self.device_details, self.discovery_results, self.fdb_observations
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
