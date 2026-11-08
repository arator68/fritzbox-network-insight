"""Home Assistant integration for FRITZ!Box Network Insight."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import FritzBoxDataUpdateCoordinator
from .fritzbox_client import FritzBoxClient
from .mac_vendor import preload_mac_vendor_registry

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
                "node_count": graph["node_count"],
                "link_count": graph["link_count"],
                "reachability_count": graph["reachability_count"],
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
                "note": "FDB is reachability evidence, not proof of a direct cable.",
            }

        hass.services.async_register(
            DOMAIN, "topology_diagnostics", async_topology_diagnostics,
            supports_response=SupportsResponse.ONLY,
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
    )
    for key in keys:
        await Store(hass, 1, key).async_remove()
    _LOGGER.info("Removed persistent FRITZ!Box Network Insight data for entry %s", entry.entry_id)
