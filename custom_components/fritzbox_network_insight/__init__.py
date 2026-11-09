"""Home Assistant integration for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator
from .device_diagnostics import device_details_snapshot
from .fritzbox_client import FritzBoxClient
from .mac_vendor import preload_mac_vendor_registry
from .topology.view_model import build_topology_view

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the FRITZ!Box connection and its sensor platform."""
    client = FritzBoxClient(
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    coordinator = FritzBoxDataUpdateCoordinator(hass, client, entry)

    await coordinator.async_load_identifications()
    await coordinator.async_load_topology()
    await coordinator.async_load_fdb_topology()
    await coordinator.async_load_manual_links()
    await coordinator.async_load_port_history()
    # IEEE vendor CSV must be read outside the HA event loop.
    await hass.async_add_executor_job(preload_mac_vendor_registry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        # Preserve the authentication failure so Home Assistant can start reauth.
        raise
    except Exception as err:
        # DataUpdateCoordinator wraps connection failures as UpdateFailed.
        _LOGGER.warning(
            "Initial FRITZ!Box host scan failed; setup will be retried: %s", err
        )
        raise ConfigEntryNotReady(
            "Could not complete the initial FRITZ!Box host scan"
        ) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    if not hass.services.has_service(DOMAIN, "device_details_diagnostics"):
        async def async_device_details_diagnostics(call):
            """Return source-tagged details without adding entities."""
            domain_data = hass.data.get(DOMAIN, {})
            requested = call.data.get("entry_id")
            if requested:
                selected = domain_data.get(requested)
            elif len(domain_data) == 1:
                selected = next(iter(domain_data.values()))
            else:
                selected = None
            if selected is None:
                return {"error": "Specify a valid entry_id (required with multiple entries)"}
            return device_details_snapshot(
                selected.device_details, call.data.get("mac")
            )

        hass.services.async_register(
            DOMAIN, "device_details_diagnostics", async_device_details_diagnostics,
            schema=vol.Schema({
                vol.Optional("entry_id"): str,
                vol.Optional("mac"): str,
            }),
            supports_response=SupportsResponse.ONLY,
        )

    if not hass.services.has_service(DOMAIN, "topology_diagnostics"):
        async def async_topology_diagnostics(call):
            """Return read-only diagnostics from the complete internal graph."""
            domain_data = hass.data.get(DOMAIN, {})
            requested = call.data.get("entry_id")
            selected = (
                domain_data.get(requested)
                if requested
                else next(iter(domain_data.values()), None)
            )
            if selected is None:
                return {"error": "No matching FRITZ!Box Network Insight entry"}
            graph = selected.get_internal_topology_graph()
            return {
                "model_version": graph["model_version"],
                "manual_links": list(selected.manual_links),
                "manual_link_count": len(selected.manual_links),
                "manual_link_checks": graph["manual_link_checks"],
                "manual_link_check_count": graph["manual_link_check_count"],
                "manual_link_port_conflict_count": graph["manual_link_port_conflict_count"],
                "node_count": graph["node_count"],
                "link_count": graph["link_count"],
                "reachability_count": graph["reachability_count"],
                "fdb_port_group_count": graph["fdb_port_group_count"],
                "fdb_port_groups": graph["fdb_port_groups"],
                "network_segment_count": graph["network_segment_count"],
                "network_segments": graph["network_segments"],
                "downstream_branches": graph["downstream_branches"],
                "downstream_branch_count": graph["downstream_branch_count"],
                "graph_branches": graph["graph_branches"],
                "graph_branch_count": graph["graph_branch_count"],
                "lan_port_memberships": graph["lan_port_memberships"],
                "lan_port_membership_count": graph["lan_port_membership_count"],
                "physical_link_candidates": graph["physical_link_candidates"],
                "physical_link_candidate_count": graph["physical_link_candidate_count"],
                "port_history": graph["port_history"],
                "port_history_count": graph["port_history_count"],
                "device_connections": graph["device_connections"],
                "device_connection_count": graph["device_connection_count"],
                "mesh_lan_observation_count": graph["mesh_lan_observation_count"],
                "mesh_lan_observations": graph["mesh_lan_observations"],
                "wlan_attachment_count": graph["wlan_attachment_count"],
                "conflict_count": graph["conflict_count"],
                "links": [
                    {
                        "source_mac": link["source_mac"],
                        "target_mac": link["target_mac"],
                        "medium": link["medium"],
                        "evidence": link["evidence"],
                        "state": link["state"],
                        "source_port": link["details"].get("source_port_id")
                            or link["details"].get("source_interface"),
                        "target_port": link["details"].get("target_port_id")
                            or link["details"].get("target_interface"),
                        "corroborated_by_avm": bool(link.get("corroboration")),
                    }
                    for link in graph["links"]
                ],
                "wlan_attachments": graph["wlan_attachments"],
                "conflicts": graph["conflicts"],
                "note": "Only LLDP confirms direct LAN cables; AVM LAN and FDB are observations.",
            }

        hass.services.async_register(
            DOMAIN, "topology_diagnostics", async_topology_diagnostics,
            supports_response=SupportsResponse.ONLY,
        )
    if not hass.services.has_service(DOMAIN, "topology_view"):
        async def async_topology_view(call):
            """Return map-ready nodes and evidence-labeled relations."""
            domain_data = hass.data.get(DOMAIN, {})
            requested = call.data.get("entry_id")
            if requested:
                selected = domain_data.get(requested)
            elif len(domain_data) == 1:
                selected = next(iter(domain_data.values()))
            else:
                selected = None
            if selected is None:
                return {"error": "Specify a valid entry_id (required with multiple entries)"}
            return build_topology_view(selected.get_internal_topology_graph())

        hass.services.async_register(
            DOMAIN, "topology_view", async_topology_view,
            schema=vol.Schema({vol.Optional("entry_id"): str}),
            supports_response=SupportsResponse.ONLY,
        )
    # Register once for all config entries. Entry selection is explicit for
    # multi-router installations; without an ID only one entry is accepted.
    def selected_coordinator(call):
        domain_data = hass.data.get(DOMAIN, {})
        entry_id = call.data.get("entry_id")
        if entry_id:
            selected = domain_data.get(entry_id)
        elif len(domain_data) == 1:
            selected = next(iter(domain_data.values()))
        else:
            selected = None
        if selected is None:
            raise ValueError("Specify a valid entry_id (required with multiple entries)")
        return selected

    if not hass.services.has_service(DOMAIN, "confirm_topology_link"):
        async def async_confirm_topology_link(call):
            selected = selected_coordinator(call)
            links = await selected.async_set_manual_link(
                call.data["source_mac"], call.data["target_mac"],
                bridge_port=call.data.get("bridge_port", ""),
                vlan_id=call.data.get("vlan_id", ""),
            )
            return {"manual_link_count": len(links), "manual_links": links}

        hass.services.async_register(
            DOMAIN, "confirm_topology_link", async_confirm_topology_link,
            schema=vol.Schema({
                vol.Optional("entry_id"): str,
                vol.Required("source_mac"): str,
                vol.Required("target_mac"): str,
                vol.Optional("bridge_port"): str,
                vol.Optional("vlan_id"): str,
            }),
            supports_response=SupportsResponse.OPTIONAL,
        )

    if not hass.services.has_service(DOMAIN, "remove_topology_link"):
        async def async_remove_topology_link(call):
            selected = selected_coordinator(call)
            links = await selected.async_delete_manual_link(
                call.data["source_mac"], call.data["target_mac"]
            )
            return {"manual_link_count": len(links), "manual_links": links}

        hass.services.async_register(
            DOMAIN, "remove_topology_link", async_remove_topology_link,
            schema=vol.Schema({
                vol.Optional("entry_id"): str,
                vol.Required("source_mac"): str,
                vol.Required("target_mac"): str,
            }),
            supports_response=SupportsResponse.OPTIONAL,
        )

    _LOGGER.info(
        "FRITZ!Box Network Insight initialized for %s with %d device(s)",
        entry.data[CONF_HOST],
        len(coordinator.data or {}),
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the configured integration entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        domain_data = hass.data.get(DOMAIN)
        if domain_data is not None:
            domain_data.pop(entry.entry_id, None)
            if not domain_data:
                hass.data.pop(DOMAIN, None)
                hass.services.async_remove(DOMAIN, "topology_diagnostics")
                hass.services.async_remove(DOMAIN, "topology_view")
                hass.services.async_remove(DOMAIN, "confirm_topology_link")
                hass.services.async_remove(DOMAIN, "remove_topology_link")
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload protocol adapters when user updates SNMP credentials."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete only persistent data owned by the removed config entry.

    Home Assistant handles the entry's entities and devices. Do not remove
    these stores on unload/reload; each key is scoped to this entry ID.
    """
    from homeassistant.helpers.storage import Store

    keys = (
        f"{DOMAIN}.identifications.{entry.entry_id}",
        f"{DOMAIN}.topology.{entry.entry_id}",
        f"{DOMAIN}.fdb.{entry.entry_id}",
        f"{DOMAIN}.manual_links.{entry.entry_id}",
        f"{DOMAIN}.port_history.{entry.entry_id}",
    )
    for key in keys:
        await Store(hass, 1, key).async_remove()
    _LOGGER.info("Removed persistent FRITZ!Box Network Insight data for entry %s", entry.entry_id)
